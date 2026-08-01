"""
WorkFlex Bridge Agent — Gradio UI.
"""

from __future__ import annotations

import os
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from controllers import process_messages, confirm_submit
from ui_templates import CUSTOM_CSS


# --------------------------------------------------------------------------- #
# Gradio UI                                                                    #
# --------------------------------------------------------------------------- #

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="WorkFlex Bridge Agent") as demo:
        # Styled App Header
        gr.HTML(
            """
            <div class="app-header">
                <h1>🔗 WorkFlex Bridge Agent</h1>
                <p>
                    Reads Teams #feature-requests, enriches each request with HubSpot ARR data, 
                    identifies duplicates in the Jira backlog, and drafts tickets or follow-up comments.
                </p>
            </div>
            """
        )

        agent_state = gr.State([])

        with gr.Row():
            max_messages = gr.Slider(
                minimum=1, maximum=50, step=1, value=20,
                label="Messages to process (newest first)",
            )
            process_btn = gr.Button("▶️ Process Messages", variant="primary")

        review_output = gr.HTML(
            "<div class='text-center py-8 text-gray-500 font-medium'>Click <strong>Process Messages</strong> to run the agent.</div>",
            label="Review",
        )

        with gr.Row():
            confirm_btn = gr.Button(
                "✅ Confirm & Submit to Jira + Teams",
                variant="primary",
                interactive=False,
            )

        results_output = gr.HTML("", visible=False)

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

        # Force dark mode class injection on load
        demo.load(
            None,
            None,
            None,
            js="""() => {
                document.body.classList.add('dark');
            }"""
        )

    return demo


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Add it to .env before running.")

    build_ui().launch(
        server_name=os.getenv("GRADIO_HOST", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_PORT", "7860")),
        theme=gr.themes.Soft(primary_hue="indigo"),
        css=CUSTOM_CSS,
    )
