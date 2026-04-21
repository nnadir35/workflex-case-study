"""
WorkFlex Bridge Agent — Gradio UI.

Two-phase workflow:

    1. "Process Messages"  → runs the LangGraph pipeline, shows what the AI
                             decided for each Teams message (UPDATE vs CREATE)
                             along with the drafted ticket/comment body.

    2. "Confirm & Submit"  → posts the drafts to Jira and sends a feedback
                             reply back to the #feature-requests Teams channel.
"""

from __future__ import annotations

import os
import traceback

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from agent import make_graph, submit_all
from clients import build_clients


# --------------------------------------------------------------------------- #
# Set up clients & compiled graph once on startup                              #
# --------------------------------------------------------------------------- #

JIRA, HUBSPOT, TEAMS = build_clients()
GRAPH = make_graph(JIRA, HUBSPOT, TEAMS)


# --------------------------------------------------------------------------- #
# Rendering helpers                                                            #
# --------------------------------------------------------------------------- #

def _render_review(items: list[dict], log: list[str]) -> str:
    if not items:
        return "_No messages to process._"

    creates = sum(1 for i in items if i.get("action") == "CREATE")
    updates = sum(1 for i in items if i.get("action") == "UPDATE")
    skipped = sum(1 for i in items if i.get("action") == "SKIP")

    lines: list[str] = []
    lines.append(
        f"### AI Decisions — **{creates}** create · **{updates}** update · "
        f"**{skipped}** skip\n"
    )
    if log:
        lines.append("<details><summary>Pipeline log</summary>\n\n" +
                     "\n".join(f"- {l}" for l in log) + "\n\n</details>\n")

    for i, item in enumerate(items, start=1):
        action = item.get("action", "SKIP")
        badge = {
            "CREATE": "🆕 **CREATE**",
            "UPDATE": "🔁 **UPDATE**",
            "SKIP":   "⏭️ **SKIP**",
        }.get(action, action)

        client = item.get("client") or "_unknown_"
        arr = item.get("arr_display", "unknown ARR")
        requester = item.get("requester") or item.get("sender") or "Unknown"

        header = f"#### {i}. {badge} — {client} · {arr}"
        if action == "UPDATE" and item.get("duplicate_ticket"):
            header += f" → **{item['duplicate_ticket']['key']}**"

        lines.append(header)
        lines.append(f"- **Requester:** {requester}")
        lines.append(f"- **Extracted request:** {item.get('request') or '_none_'}")
        if item.get("hubspot_match") and item["hubspot_match"] != client:
            lines.append(f"- **HubSpot match:** {item['hubspot_match']}")
        if action == "UPDATE":
            parent = item["duplicate_ticket"]
            lines.append(f"- **Duplicate of:** `{parent['key']}` — {parent['summary']}")

        if action == "CREATE":
            lines.append("")
            lines.append("**Drafted new ticket:**")
            lines.append(f"> **Title:** {item.get('draft_title') or '_(empty)_'}")
            if item.get("draft_body"):
                body = item["draft_body"].replace("\n", "\n> ")
                lines.append(f"> \n> {body}")
        elif action == "UPDATE":
            lines.append("")
            lines.append("**Drafted comment:**")
            if item.get("draft_body"):
                body = item["draft_body"].replace("\n", "\n> ")
                lines.append(f"> {body}")

        if item.get("error"):
            lines.append(f"\n⚠️ _{item['error']}_")

        lines.append("\n---\n")

    return "\n".join(lines)


def _render_results(results: list[dict]) -> str:
    if not results:
        return "_No items were submitted._"

    ok = sum(1 for r in results if r.get("ok") and not r.get("skipped"))
    skipped = sum(1 for r in results if r.get("skipped"))
    failed = sum(1 for r in results if not r.get("ok"))

    lines = [
        f"### Submission Complete — **{ok}** succeeded · "
        f"**{skipped}** skipped · **{failed}** failed\n"
    ]
    for i, r in enumerate(results, start=1):
        if r.get("skipped"):
            lines.append(f"{i}. ⏭️  Skipped (no request extracted)")
            continue
        if not r.get("ok"):
            lines.append(f"{i}. ❌ Failed — `{r.get('error')}`")
            continue
        action = r.get("action", "?")
        icon = "🆕" if action == "CREATE" else "🔁"
        lines.append(f"{i}. {icon} **{action}** `{r.get('ticket_key')}` — {r.get('feedback')}")
    return "\n".join(lines)


def _render_live_submit_log(log_lines: list[str], done: bool = False) -> str:
    title = "### 🚀 Submit in progress..." if not done else "### ✅ Submit completed"
    body = "\n".join(f"- {line}" for line in log_lines) if log_lines else "- Starting..."
    return f"{title}\n\n{body}"


def _render_fatal_error(title: str, exc: Exception) -> str:
    details = f"{type(exc).__name__}: {exc}"
    return (
        f"### ❌ {title}\n"
        "İşlem tamamlanamadı. Lütfen ayarları kontrol edip tekrar deneyin.\n\n"
        f"- **Hata:** `{details}`\n"
        "- **Kontrol et:** `MOCK_API_BASE_URL`, servis token'ları, `ANTHROPIC_API_KEY`\n"
        "- **Not:** Teknik traceback terminalde tutulur."
    )


# --------------------------------------------------------------------------- #
# Gradio callbacks                                                             #
# --------------------------------------------------------------------------- #

def process_messages(max_messages: int, progress=gr.Progress(track_tqdm=False)):
    """Run the LangGraph pipeline up through drafting, ready for human review."""
    progress(0.0, desc="Connecting to mock APIs…")
    initial = {
        "messages": [],
        "backlog": [],
        "items": [],
        "max_messages": int(max_messages),
        "log": [],
    }
    progress(0.1, desc="Running LangGraph pipeline (this calls Claude per message)…")
    try:
        final_state = GRAPH.invoke(initial)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        return (
            [],                                        # agent_state
            _render_fatal_error("Process Messages başarısız", e),
            gr.update(interactive=False),              # confirm_btn
            gr.update(value="", visible=False),        # results_output
        )
    progress(1.0, desc="Drafts ready for review.")

    items = final_state.get("items", [])
    review_md = _render_review(items, final_state.get("log", []))

    # Enable the confirm button only if there's at least one actionable item.
    actionable = any(i.get("action") in ("CREATE", "UPDATE") for i in items)
    return (
        items,                                   # agent_state
        review_md,                               # review_output
        gr.update(interactive=actionable),       # confirm_btn
        gr.update(value="", visible=False),      # results_output
    )


def confirm_submit(items: list[dict], progress=gr.Progress(track_tqdm=False)):
    """Post approved drafts to Jira + send feedback back to Teams."""
    if not items:
        yield gr.update(
            value="_Nothing to submit. Click **Process Messages** first._",
            visible=True,
        )
        return

    actionable = [i for i in items if i.get("action") in ("CREATE", "UPDATE")]
    if not actionable:
        yield gr.update(
            value="_No actionable drafts (CREATE/UPDATE) to submit._",
            visible=True,
        )
        return

    results: list[dict] = []
    live_lines: list[str] = []
    total = len(actionable)

    for idx, item in enumerate(actionable, start=1):
        action = item.get("action")
        client_name = item.get("client") or "unknown client"
        arr_display = item.get("arr_display", "unknown ARR")
        progress((idx - 1) / max(total, 1), desc=f"Submitting {idx}/{total}…")
        live_lines.append(f"[{idx}/{total}] Start `{action}` for **{client_name}** ({arr_display})")
        yield gr.update(value=_render_live_submit_log(live_lines), visible=True)

        result: dict = {
            "message_id": item.get("message_id"),
            "requester": item.get("requester"),
            "client": item.get("client"),
            "action": action,
            "ok": False,
        }

        try:
            if action == "UPDATE":
                parent_key = item["duplicate_ticket"]["key"]
                live_lines.append(f"[{idx}/{total}] Jira comment → `{parent_key}`")
                yield gr.update(value=_render_live_submit_log(live_lines), visible=True)
                JIRA.add_comment(parent_key, item["draft_body"])

                feedback = f"Got it! Added to Ticket #{parent_key}"
                live_lines.append(f"[{idx}/{total}] Teams feedback posted")
                yield gr.update(value=_render_live_submit_log(live_lines), visible=True)
                TEAMS.post_message(feedback)

                result.update(ok=True, ticket_key=parent_key, feedback=feedback)
                live_lines.append(f"[{idx}/{total}] ✅ Done UPDATE `{parent_key}`")

            elif action == "CREATE":
                live_lines.append(f"[{idx}/{total}] Jira issue creating")
                yield gr.update(value=_render_live_submit_log(live_lines), visible=True)
                created = JIRA.create_issue(
                    summary=item.get("draft_title") or item.get("request", "New feature request"),
                    description=item.get("draft_body", ""),
                )
                new_key = created["key"]

                feedback = f"Created new Ticket #{new_key} for {client_name} ({arr_display})"
                live_lines.append(f"[{idx}/{total}] Teams feedback posted")
                yield gr.update(value=_render_live_submit_log(live_lines), visible=True)
                TEAMS.post_message(feedback)

                result.update(ok=True, ticket_key=new_key, feedback=feedback)
                live_lines.append(f"[{idx}/{total}] ✅ Done CREATE `{new_key}`")

        except Exception as e:  # noqa: BLE001
            result.update(ok=False, error=str(e))
            live_lines.append(f"[{idx}/{total}] ❌ Failed: `{type(e).__name__}: {e}`")
            traceback.print_exc()

        results.append(result)
        yield gr.update(value=_render_live_submit_log(live_lines), visible=True)

    progress(1.0, desc="Done.")
    yield gr.update(value=f"{_render_live_submit_log(live_lines, done=True)}\n\n{_render_results(results)}", visible=True)


# --------------------------------------------------------------------------- #
# Gradio UI                                                                    #
# --------------------------------------------------------------------------- #

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="WorkFlex Bridge Agent") as demo:
        gr.Markdown(
            "# 🔗 WorkFlex Bridge Agent\n"
            "Reads Teams `#feature-requests`, enriches each request with HubSpot "
            "ARR data, matches against the Jira backlog, and drafts either a "
            "new ticket or a follow-up comment — all powered by Claude + LangGraph. "
            "Drafts are shown below for review. Nothing is written until you hit "
            "**Confirm & Submit**."
        )

        agent_state = gr.State([])

        with gr.Row():
            max_messages = gr.Slider(
                minimum=1, maximum=50, step=1, value=20,
                label="Messages to process (newest first)",
            )
            process_btn = gr.Button("▶️ Process Messages", variant="primary")

        review_output = gr.Markdown(
            "_Click **Process Messages** to run the agent._",
            label="Review",
        )

        with gr.Row():
            confirm_btn = gr.Button(
                "✅ Confirm & Submit to Jira + Teams",
                variant="primary",
                interactive=False,
            )

        results_output = gr.Markdown("", visible=False)

        process_btn.click(
            fn=process_messages,
            inputs=[max_messages],
            outputs=[agent_state, review_output, confirm_btn, results_output],
        )
        confirm_btn.click(
            fn=confirm_submit,
            inputs=[agent_state],
            outputs=[results_output],
        )

    return demo


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Add it to .env before running.")

    build_ui().launch(
        server_name=os.getenv("GRADIO_HOST", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_PORT", "7860")),
        theme=gr.themes.Soft(primary_hue="indigo"),
    )
