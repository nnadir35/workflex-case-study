import time
import traceback
from concurrent.futures import ThreadPoolExecutor
import gradio as gr

from agent import make_graph, submit_all
from clients import build_clients
from ui_templates import render_review, render_results, render_live_submit_log, render_fatal_error

# Initialize the clients and the LangGraph once for the controller
JIRA, HUBSPOT, TEAMS = build_clients()
GRAPH = make_graph(JIRA, HUBSPOT, TEAMS)


def process_messages(max_messages: int, progress=gr.Progress(track_tqdm=False)):
    """Run the LangGraph pipeline up through drafting, ready for review."""
    progress(0.0, desc="Connecting to mock APIs…")
    initial = {
        "messages": [],
        "backlog": [],
        "items": [],
        "max_messages": int(max_messages),
        "log": [],
    }
    progress(0.02, desc="Initializing pipeline...")
    yield (
        [],
        (
            "<div class='text-center py-12 text-gray-500 font-medium'>"
            "   <div style='display:inline-block; border: 4px solid #f3f3f3; border-top: 4px solid #4f46e5; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 1rem;'></div>"
            "   <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>"
            "   <div>Processing messages & generating recommendations... Please wait.</div>"
            "</div>"
        ),
        gr.update(interactive=False),
        gr.update(value="", visible=False),
    )

    started = time.time()
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(GRAPH.invoke, initial)
        heartbeat = 0
        while not future.done():
            heartbeat += 1
            elapsed = time.time() - started
            p = min(0.05 + heartbeat * 0.02, 0.92)
            progress(
                p,
                desc=(
                    f"Processing messages... "
                    f"(running {int(elapsed)}s)"
                ),
            )
            dots = "." * ((heartbeat % 3) + 1)
            yield (
                [],
                (
                    f"<div class='text-center py-12 text-gray-500 font-medium'>"
                    f"   <div style='display:inline-block; border: 4px solid #f3f3f3; border-top: 4px solid #4f46e5; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 1rem;'></div>"
                    f"   <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>"
                    f"   <div>Pipeline running{dots} ({int(elapsed)}s elapsed)</div>"
                    f"</div>"
                ),
                gr.update(interactive=False),
                gr.update(value="", visible=False),
            )
            time.sleep(0.8)

        try:
            final_state = future.result()
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            yield (
                [],
                render_fatal_error("Process Messages failed", e),
                gr.update(interactive=False),
                gr.update(value="", visible=False),
            )
            return

    progress(1.0, desc="Drafts ready for review.")

    items = final_state.get("items", [])
    review_html = render_review(items, final_state.get("log", []))

    # Enable the confirm button only if there's at least one actionable item.
    actionable = any(i.get("action") in ("CREATE", "UPDATE") for i in items)
    yield (
        items,                                   # agent_state
        review_html,                             # review_output
        gr.update(interactive=actionable),       # confirm_btn
        gr.update(value="", visible=False),      # results_output
    )


def confirm_submit(items: list[dict], progress=gr.Progress(track_tqdm=False)):
    """Post approved drafts to Jira + send feedback back to Teams."""
    if not items:
        yield gr.update(
            value="<div class='error-banner'>Nothing to submit. Click Process Messages first.</div>",
            visible=True,
        )
        return

    actionable = [i for i in items if i.get("action") in ("CREATE", "UPDATE")]
    if not actionable:
        yield gr.update(
            value="<div class='error-banner'>No actionable drafts to submit.</div>",
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
        yield gr.update(value=render_live_submit_log(live_lines), visible=True)

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
                yield gr.update(value=render_live_submit_log(live_lines), visible=True)
                JIRA.add_comment(parent_key, item["draft_body"])

                feedback = f"Got it! Added to Ticket #{parent_key}"
                live_lines.append(f"[{idx}/{total}] Teams feedback posted")
                yield gr.update(value=render_live_submit_log(live_lines), visible=True)
                TEAMS.post_message(feedback)

                result.update(ok=True, ticket_key=parent_key, feedback=feedback)
                live_lines.append(f"[{idx}/{total}] ✅ Done UPDATE `{parent_key}`")

            elif action == "CREATE":
                live_lines.append(f"[{idx}/{total}] Jira issue creating")
                yield gr.update(value=render_live_submit_log(live_lines), visible=True)
                created = JIRA.create_issue(
                    summary=item.get("draft_title") or item.get("request", "New feature request"),
                    description=item.get("draft_body", ""),
                )
                new_key = created["key"]

                feedback = f"Created new Ticket #{new_key} for {client_name} ({arr_display})"
                live_lines.append(f"[{idx}/{total}] Teams feedback posted")
                yield gr.update(value=render_live_submit_log(live_lines), visible=True)
                TEAMS.post_message(feedback)

                result.update(ok=True, ticket_key=new_key, feedback=feedback)
                live_lines.append(f"[{idx}/{total}] ✅ Done CREATE `{new_key}`")

        except Exception as e:  # noqa: BLE001
            result.update(ok=False, error=str(e))
            live_lines.append(f"[{idx}/{total}] ❌ Failed: `{type(e).__name__}: {e}`")
            traceback.print_exc()

        results.append(result)
        yield gr.update(value=render_live_submit_log(live_lines), visible=True)

    progress(1.0, desc="Done.")
    yield gr.update(value=f"{render_live_submit_log(live_lines, done=True)}\n\n{render_results(results)}", visible=True)
