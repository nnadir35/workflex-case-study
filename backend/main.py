import gradio as gr
import anthropic, os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def chat(message, history):
    messages = []
    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        messages.append({"role": "assistant", "content": assistant})
    messages.append({"role": "user", "content": message})
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=messages
    )
    return response.content[0].text

demo = gr.ChatInterface(
    fn=chat,
    title="WorkFlex AI Assistant",
    description="Internal AI tool for compliance and operations"
)

if __name__ == "__main__":
    demo.launch()