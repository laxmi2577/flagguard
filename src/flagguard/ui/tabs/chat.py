"""Chat tab for RAG-powered Q&A."""

import gradio as gr
from pathlib import Path
from flagguard.rag.engine import ChatEngine
from flagguard.rag.ingester import CodebaseIngester
from flagguard.core.logging import get_logger

logger = get_logger("ui.chat")

def create_chat_tab(app_state: dict) -> None:
    """Create the AI Chat tab."""
    
    with gr.Tab("💬 AI Chat", id="tab_chat"):
        gr.Markdown("### 🤖 Chat with your Flags\nAsk questions about your feature flags, dependencies, and code usage.")
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="FlagGuard AI",
                    height=500,
                    avatar_images=(None, "https://api.iconify.design/logos:python.svg")
                )
                msg = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., Where is the 'dark_mode' flag used?",
                    show_label=False,
                    container=False,
                    scale=7
                )
                with gr.Row():
                    submit_btn = gr.Button("Send 🚀", variant="primary", scale=1)
                    clear_btn = gr.Button("Clear Chat", variant="secondary", scale=1)
            
            with gr.Column(scale=1):
                gr.Markdown("### 📚 Knowledge Base")
                index_status = gr.Textbox(label="Index Status", value="Not Indexed", interactive=False)
                index_btn = gr.Button("🔄 Index Codebase", variant="primary")
                
                gr.Markdown("""
                **How it works:**
                1. Click **Index Codebase** to scan your project.
                2. Ask questions about flags or code logic.
                3. The AI retrieves relevant code snippets to answer.
                """)
                
                gr.Markdown("### 💡 Example Questions")
                gr.Examples(
                    examples=[
                        "List all defined feature flags.",
                        "Where is the 'new_checkout_flow' flag used?",
                        "What happens if I disable 'beta_features'?",
                        "Are there any conflicting flags?",
                    ],
                    inputs=msg
                )

        # Chat Engine Instance (lazy loading)
        chat_engine = None
        
        def get_engine():
            nonlocal chat_engine
            if chat_engine is None:
                chat_engine = ChatEngine()
            return chat_engine

        def user(user_message, history):
            if history is None:
                history = []
            return "", history + [{"role": "user", "content": user_message}]

        def bot(history):
            if not history:
                return history
                
            # Last message is from user
            user_message = history[-1]["content"]
            
            try:
                engine = get_engine()
                # Streaming response could be added here later
                response = engine.chat(user_message)
                
                history.append({"role": "assistant", "content": response})
            except Exception as e:
                logger.error(f"Chat error: {e}")
                history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
                
            return history

        def index_codebase():
            try:
                # Get paths from app state (assuming they are set in main app)
                # Fallback to current directory for demo if not set
                workspace = "." 
                
                # Auto-detect configuration file
                if Path(".flagguard.yaml").exists():
                    config = ".flagguard.yaml"
                elif Path("flags.json").exists():
                    config = "flags.json"
                elif Path("flags.yaml").exists():
                    config = "flags.yaml"
                else:
                    return "❌ Error: Could not find .flagguard.yaml or flags.json in root directory."
                
                ingester = CodebaseIngester(workspace, config)
                count = ingester.ingest()
                return f"✅ Indexed {count} documents"
            except Exception as e:
                logger.error(f"Ingestion error: {e}")
                return f"❌ Error: {str(e)}"

        # Event Handlers
        msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        )
        submit_btn.click(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        )
        clear_btn.click(lambda: None, None, chatbot, queue=False)
        
        index_btn.click(index_codebase, outputs=index_status)
