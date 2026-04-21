"""
LangGraph workflow for the WorkFlex Bridge Agent.

Pipeline (compiled as a LangGraph StateGraph):

    fetch_messages ──► fetch_backlog ──► extract ──► enrich_arr ──► match_duplicate ──► draft

`draft` is the final node of the *review* phase: its output is shown in the UI
for human approval. The `submit_all` function below is invoked separately
after the user clicks "Confirm" — it posts drafts to Jira and Teams.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional, TypedDict

from anthropic import Anthropic
from langgraph.graph import END, START, StateGraph

from clients import HubSpotClient, JiraClient, TeamsClient, adf_to_text


MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


# --------------------------------------------------------------------------- #
# LangGraph state                                                              #
# --------------------------------------------------------------------------- #

class Item(TypedDict, total=False):
    """One processed Teams message + its downstream analysis."""
    message_id: str
    sender: str
    text: str
    requester: str
    client: str
    request: str
    arr: Optional[int]
    arr_display: str
    hubspot_match: Optional[str]
    duplicate_ticket: Optional[dict]  # {"key": str, "summary": str}
    action: str                       # "UPDATE" | "CREATE"
    draft_title: Optional[str]
    draft_body: str
    error: Optional[str]


class AgentState(TypedDict):
    messages: list[dict]     # Raw Teams messages
    backlog: list[dict]      # Existing Jira issues (condensed form: key/title/desc)
    items: list[Item]
    max_messages: int
    log: list[str]


# --------------------------------------------------------------------------- #
# Claude helpers                                                               #
# --------------------------------------------------------------------------- #

_anthropic: Anthropic | None = None


def _claude() -> Anthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic


def _call_claude_json(system: str, user: str, max_tokens: int = 600) -> dict:
    """Call Claude and parse a JSON object out of its reply."""
    resp = _claude().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()

    # Claude sometimes wraps JSON in ```json ... ``` fences — strip them.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)

    return json.loads(text)


# --------------------------------------------------------------------------- #
# Formatting helpers                                                           #
# --------------------------------------------------------------------------- #

def format_arr(arr: int | None) -> str:
    if arr is None:
        return "unknown ARR"
    if arr >= 1_000_000:
        return f"${arr / 1_000_000:.1f}M ARR"
    if arr >= 1_000:
        return f"${arr // 1_000}k ARR"
    return f"${arr} ARR"


def _backlog_catalog(backlog: list[dict]) -> str:
    lines = []
    for t in backlog:
        desc = t.get("description", "").strip().replace("\n", " ")
        if len(desc) > 220:
            desc = desc[:217] + "..."
        lines.append(f"- {t['key']}: {t['summary']}\n  {desc}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Graph nodes                                                                  #
# --------------------------------------------------------------------------- #

def make_graph(jira: JiraClient, hubspot: HubSpotClient, teams: TeamsClient):
    """Build and compile the LangGraph StateGraph."""

    # ---- Node: fetch Teams messages ---- #
    def fetch_messages(state: AgentState) -> AgentState:
        raw = teams.list_messages(top=50)

        # Ignore bot-authored messages (the agent's own feedback) and stay
        # within max_messages. The mock server returns newest first.
        human_msgs = [
            m for m in raw
            if (m.get("from") or {}).get("user") is not None
        ][: state.get("max_messages", 10)]

        # Oldest-first for a more natural review order in the UI.
        human_msgs.reverse()

        return {
            **state,
            "messages": human_msgs,
            "log": state.get("log", []) + [f"Fetched {len(human_msgs)} Teams messages."],
        }

    # ---- Node: fetch Jira backlog ---- #
    def fetch_backlog(state: AgentState) -> AgentState:
        issues = jira.search_issues(max_results=200)
        condensed = [
            {
                "key": i["key"],
                "summary": i["fields"]["summary"],
                "description": adf_to_text(i["fields"].get("description")),
            }
            for i in issues
        ]
        return {
            **state,
            "backlog": condensed,
            "log": state["log"] + [f"Loaded {len(condensed)} existing Jira tickets."],
        }

    # ---- Node: extract structured fields from each message ---- #
    def extract(state: AgentState) -> AgentState:
        system = (
            "You extract structured fields from a single Microsoft Teams "
            "message posted in the #feature-requests channel. "
            "Return ONLY a JSON object with keys: requester, client, request. "
            "- `requester`: the Teams user who wrote the message (string). "
            "- `client`: the customer/company mentioned in the message, or empty string if none. "
            "- `request`: a concise (<= 240 chars) paraphrase of the feature request or ask. "
            "If there is no clear feature request, set `request` to an empty string."
        )

        items: list[Item] = []
        for m in state["messages"]:
            sender = (m.get("from") or {}).get("user", {}).get("displayName") or "Unknown"
            text = (m.get("body") or {}).get("content", "").strip()
            user = (
                f"Sender (displayName): {sender}\n"
                f"Message:\n\"\"\"\n{text}\n\"\"\"\n\n"
                "Respond with the JSON object."
            )
            try:
                data = _call_claude_json(system, user, max_tokens=300)
                items.append({
                    "message_id": m["id"],
                    "sender": sender,
                    "text": text,
                    "requester": (data.get("requester") or sender).strip(),
                    "client": (data.get("client") or "").strip(),
                    "request": (data.get("request") or "").strip(),
                })
            except Exception as e:  # noqa: BLE001
                items.append({
                    "message_id": m["id"],
                    "sender": sender,
                    "text": text,
                    "requester": sender,
                    "client": "",
                    "request": "",
                    "error": f"extract failed: {e}",
                })

        return {
            **state,
            "items": items,
            "log": state["log"] + [f"Extracted fields for {len(items)} messages."],
        }

    # ---- Node: look up the client's ARR in HubSpot ---- #
    def enrich_arr(state: AgentState) -> AgentState:
        updated: list[Item] = []
        for item in state["items"]:
            client_name = item.get("client") or ""
            arr: int | None = None
            match_name: str | None = None
            if client_name:
                try:
                    co = hubspot.search_company(client_name)
                    if co:
                        arr = HubSpotClient.get_arr(co)
                        match_name = co.get("properties", {}).get("name")
                except Exception as e:  # noqa: BLE001
                    item = {**item, "error": f"hubspot lookup failed: {e}"}
            updated.append({
                **item,
                "arr": arr,
                "arr_display": format_arr(arr),
                "hubspot_match": match_name,
            })

        found = sum(1 for i in updated if i.get("arr") is not None)
        return {
            **state,
            "items": updated,
            "log": state["log"] + [f"Enriched ARR for {found}/{len(updated)} clients from HubSpot."],
        }

    # ---- Node: search the Jira backlog for a duplicate ---- #
    def match_duplicate(state: AgentState) -> AgentState:
        catalog = _backlog_catalog(state["backlog"])
        system = (
            "You are helping a product team triage incoming feature requests. "
            "Given a new feature request and a catalog of existing Jira backlog tickets, "
            "determine whether the new request is a DUPLICATE of (i.e. substantially the "
            "same as) any existing ticket. "
            "Two requests should be considered duplicates only if they ask for the same "
            "capability. Cosmetic rewording is fine; different features are NOT duplicates. "
            "Respond with ONLY a JSON object: "
            '{"duplicate_key": "JIRA-XXXX" or null, "reason": "short explanation"}'
        )

        updated: list[Item] = []
        by_key = {t["key"]: t for t in state["backlog"]}

        for item in state["items"]:
            if not item.get("request"):
                updated.append({**item, "duplicate_ticket": None, "action": "SKIP"})
                continue

            user = (
                f"New feature request:\n"
                f"- Client: {item.get('client') or 'unknown'}\n"
                f"- Request: {item['request']}\n\n"
                f"Existing backlog:\n{catalog}\n\n"
                "Return the JSON object."
            )
            dup_key = None
            try:
                data = _call_claude_json(system, user, max_tokens=300)
                candidate = data.get("duplicate_key")
                if candidate and candidate in by_key:
                    dup_key = candidate
            except Exception as e:  # noqa: BLE001
                item = {**item, "error": f"match failed: {e}"}

            if dup_key:
                dup_ticket = {
                    "key": dup_key,
                    "summary": by_key[dup_key]["summary"],
                }
                updated.append({**item, "duplicate_ticket": dup_ticket, "action": "UPDATE"})
            else:
                updated.append({**item, "duplicate_ticket": None, "action": "CREATE"})

        creates = sum(1 for i in updated if i.get("action") == "CREATE")
        updates = sum(1 for i in updated if i.get("action") == "UPDATE")
        skipped = sum(1 for i in updated if i.get("action") == "SKIP")
        return {
            **state,
            "items": updated,
            "log": state["log"]
            + [f"Matched: {creates} CREATE, {updates} UPDATE, {skipped} SKIP."],
        }

    # ---- Node: draft the final ticket/comment body ---- #
    def draft(state: AgentState) -> AgentState:
        create_system = (
            "You draft Jira tickets for a SaaS product team. "
            "Given a customer feature request, produce a JSON object with keys "
            "`title` and `body`. "
            "- `title`: a concise Jira-style ticket summary (<= 90 chars). "
            "- `body`: a short, clearly formatted description (3-8 lines) that states the "
            "user problem, proposed solution, and customer context. "
            "Include the customer name and ARR in the body. Do not fabricate details."
        )
        update_system = (
            "You draft Jira comments that add new customer context to an existing ticket. "
            "Given a new request, the parent ticket summary, and customer info, produce a "
            "JSON object with key `body` only. The comment should be 2-5 lines, begin with "
            "'Additional customer request from <requester>', mention the client name and "
            "ARR, and briefly summarize the new ask."
        )

        updated: list[Item] = []
        for item in state["items"]:
            if item.get("action") == "SKIP":
                updated.append({**item, "draft_title": None, "draft_body": ""})
                continue

            client = item.get("client") or "unknown client"
            arr_display = item.get("arr_display", "unknown ARR")
            requester = item.get("requester") or item.get("sender", "Unknown")
            request = item.get("request", "")

            try:
                if item["action"] == "UPDATE":
                    parent = item["duplicate_ticket"]
                    user = (
                        f"Parent ticket: {parent['key']} — {parent['summary']}\n"
                        f"Requester: {requester}\n"
                        f"Client: {client} ({arr_display})\n"
                        f"New request: {request}\n\n"
                        "Return the JSON object."
                    )
                    data = _call_claude_json(update_system, user, max_tokens=400)
                    updated.append({
                        **item,
                        "draft_title": None,
                        "draft_body": (data.get("body") or "").strip(),
                    })
                else:  # CREATE
                    user = (
                        f"Requester: {requester}\n"
                        f"Client: {client} ({arr_display})\n"
                        f"Request: {request}\n\n"
                        "Return the JSON object."
                    )
                    data = _call_claude_json(create_system, user, max_tokens=500)
                    updated.append({
                        **item,
                        "draft_title": (data.get("title") or request[:80]).strip(),
                        "draft_body": (data.get("body") or "").strip(),
                    })
            except Exception as e:  # noqa: BLE001
                updated.append({
                    **item,
                    "draft_title": request[:80] if item["action"] == "CREATE" else None,
                    "draft_body": f"(draft generation failed: {e})",
                    "error": f"draft failed: {e}",
                })

        return {
            **state,
            "items": updated,
            "log": state["log"] + ["Drafted ticket/comment bodies."],
        }

    g = StateGraph(AgentState)
    g.add_node("fetch_messages", fetch_messages)
    g.add_node("fetch_backlog", fetch_backlog)
    g.add_node("extract", extract)
    g.add_node("enrich_arr", enrich_arr)
    g.add_node("match_duplicate", match_duplicate)
    g.add_node("draft", draft)

    g.add_edge(START, "fetch_messages")
    g.add_edge("fetch_messages", "fetch_backlog")
    g.add_edge("fetch_backlog", "extract")
    g.add_edge("extract", "enrich_arr")
    g.add_edge("enrich_arr", "match_duplicate")
    g.add_edge("match_duplicate", "draft")
    g.add_edge("draft", END)

    return g.compile()


# --------------------------------------------------------------------------- #
# Submit phase (runs after human approval in the UI)                           #
# --------------------------------------------------------------------------- #

def submit_all(
    jira: JiraClient,
    teams: TeamsClient,
    items: list[Item],
) -> list[dict[str, Any]]:
    """
    Apply each drafted item to Jira (create/comment) and post a feedback
    message back to the Teams channel. Returns a per-item results list.
    """
    results: list[dict[str, Any]] = []

    for item in items:
        action = item.get("action")
        result: dict[str, Any] = {
            "message_id": item["message_id"],
            "requester": item.get("requester"),
            "client": item.get("client"),
            "action": action,
            "ok": False,
        }

        try:
            if action == "UPDATE":
                parent_key = item["duplicate_ticket"]["key"]
                jira.add_comment(parent_key, item["draft_body"])
                feedback = f"Got it! Added to Ticket #{parent_key}"
                teams.post_message(feedback)
                result.update(ok=True, ticket_key=parent_key, feedback=feedback)

            elif action == "CREATE":
                created = jira.create_issue(
                    summary=item["draft_title"] or item.get("request", "New feature request"),
                    description=item["draft_body"],
                )
                new_key = created["key"]
                client_name = item.get("client") or "a customer"
                arr_display = item.get("arr_display", "unknown ARR")
                feedback = (
                    f"Created new Ticket #{new_key} for {client_name} ({arr_display})"
                )
                teams.post_message(feedback)
                result.update(ok=True, ticket_key=new_key, feedback=feedback)

            else:  # SKIP
                result.update(ok=True, skipped=True)

        except Exception as e:  # noqa: BLE001
            result.update(ok=False, error=str(e))

        results.append(result)

    return results
