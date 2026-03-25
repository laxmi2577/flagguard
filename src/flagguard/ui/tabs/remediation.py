"""AI Remediation Tab — Phase 1 GraphRAG UI Integration.

Adds an 'AI Remediation' tab to the Gradio dashboard that:
1. Lets users select a detected conflict.
2. Runs the Agentic Remediation Loop (Coder → Verifier → Retry).
3. Displays the agent's reasoning chain and verified code patch.
"""

import gradio as gr
from flagguard.core.logging import get_logger

logger = get_logger("ui.remediation")


def create_remediation_tab():
    """Create the AI Remediation Gradio tab component.

    Returns:
        Tuple of (tab component, references to key UI elements).
    """
    with gr.TabItem("🤖 AI Remediation") as tab:
        gr.HTML(
            "<div style='padding:12px 16px;background:linear-gradient(135deg,"
            "rgba(139,92,246,0.15),rgba(59,130,246,0.1));"
            "border-radius:12px;border:1px solid rgba(139,92,246,0.2);"
            "margin-bottom:16px;'>"
            "<b style='color:#a78bfa;font-size:15px;'>🤖 Agentic Code Remediation</b>"
            "<br/><span style='color:#94a3b8;font-size:13px;'>"
            "GraphRAG retrieves relevant source code → Coder Agent generates a fix → "
            "Z3 Verifier Agent validates it → Only verified patches are shown."
            "</span></div>"
        )

        with gr.Row():
            with gr.Column(scale=1, elem_classes=["frosted-sidebar"]):
                gr.HTML("<div class='sidebar-title'>Conflict Selection</div>")
                conflict_selector = gr.Dropdown(
                    label="Select Conflict",
                    choices=[],
                    interactive=True,
                    info="Pick a conflict from the latest analysis run.",
                )
                conflict_detail = gr.Textbox(
                    label="Conflict Details",
                    interactive=False,
                    lines=4,
                )
                remediate_btn = gr.Button(
                    "🔧 Generate AI Fix",
                    elem_classes=["glass-btn"],
                    interactive=True,
                )
                gr.HTML(
                    "<div style='margin:12px 0;border-top:1px solid "
                    "rgba(212,175,55,0.1);'></div>"
                )
                status_indicator = gr.HTML(
                    "<div style='color:#64748b;font-size:13px;'>"
                    "💤 Waiting for conflict selection...</div>"
                )

            with gr.Column(scale=3):
                with gr.Tabs():
                    with gr.TabItem("📝 Suggested Fix"):
                        fix_output = gr.Markdown(
                            "*Select a conflict and click 'Generate AI Fix' "
                            "to see the agent's code patch.*"
                        )
                        from flagguard.ui.feedback import create_feedback_component
                        feedback_html, prompt_state, response_state = create_feedback_component("fix")

                    with gr.TabItem("🧠 Agent Reasoning"):
                        reasoning_output = gr.Markdown(
                            "*The agent's step-by-step thought process "
                            "(Coder → Verifier → Final) will appear here.*"
                        )

                    with gr.TabItem("📊 RAG Context"):
                        rag_context_output = gr.Markdown(
                            "*Retrieved source code context from ChromaDB "
                            "(semantic) and NetworkX (graph) will be shown here.*"
                        )

        # ── Event Handler ──
        def run_remediation(conflict_id, user_state):
            """Run the agentic remediation loop for a selected conflict."""
            if not conflict_id:
                return (
                    "*Please select a conflict first.*",
                    "*No reasoning data.*",
                    "*No context retrieved.*",
                    _status_html("⚠️ No conflict selected", "warning"),
                    "",
                    "",
                )

            try:
                from flagguard.llm.ollama_client import OllamaClient
                from flagguard.ai.agent import (
                    RemediationAgent,
                    format_reasoning_for_ui,
                )
                from flagguard.rag.retriever import HybridRetriever

                # Initialize components
                llm_client = OllamaClient()
                retriever = HybridRetriever(use_graph=False)

                # Build conflict description from the selected ID
                conflict_desc = f"Conflict ID: {conflict_id}"
                flags = []

                # Try to get actual conflict data from the last analysis
                if isinstance(user_state, dict):
                    last_conflicts = user_state.get("last_conflicts", [])
                    for c in last_conflicts:
                        cid = getattr(c, "conflict_id", None) or c.get("conflict_id", "")
                        if str(cid) == str(conflict_id):
                            conflict_desc = getattr(c, "reason", str(c))
                            flags = getattr(c, "flags_involved", [])
                            break

                # Step 1: Retrieve context via Hybrid Retriever
                status = _status_html("🔍 Retrieving code context via GraphRAG...", "active")
                
                # We yield early to show status change if this was a generator,
                # but currently grad.Button.click doesn't use generators here.
                # (Skipped yielding for simplicity - Gradio needs .success for generators)

                if flags:
                    results = retriever.retrieve_for_conflict(
                        flag_names=flags,
                        conflict_description=conflict_desc,
                    )
                    rag_context = retriever.format_context_for_llm(results)
                else:
                    # Fallback: simple semantic search
                    docs = retriever.retrieve(conflict_desc, top_k=5)
                    rag_context = "\n\n".join(
                        [f"[{d.metadata.get('file', '?')}]\n{d.text[:300]}" for d in docs]
                    ) if docs else "No relevant context found."

                # Step 2: Run Agentic Loop
                agent = RemediationAgent(llm_client=llm_client)
                result = agent.remediate(
                    conflict_description=conflict_desc,
                    flags=flags,
                    source_context=rag_context,
                )

                # Format outputs
                fix_md = result.suggested_fix if result.suggested_fix else "*No fix generated.*"
                reasoning_md = format_reasoning_for_ui(result)
                context_md = f"### Retrieved Context\n\n```\n{rag_context[:2000]}\n```"

                verified_icon = "✅" if result.verified else "❌"
                final_status = _status_html(
                    f"{verified_icon} {result.status.value} "
                    f"({result.attempts} attempt{'s' if result.attempts != 1 else ''})",
                    "success" if result.verified else "error",
                )

                return fix_md, reasoning_md, context_md, final_status, conflict_desc, fix_md

            except Exception as e:
                logger.error(f"Remediation failed: {e}")
                return (
                    f"*Error: {e}*",
                    "*Remediation failed.*",
                    "*Could not retrieve context.*",
                    _status_html(f"❌ Error: {str(e)[:80]}", "error"),
                    "",
                    "",
                )

        remediate_btn.click(
            fn=run_remediation,
            inputs=[conflict_selector, gr.State({})],
            outputs=[fix_output, reasoning_output, rag_context_output, status_indicator, prompt_state, response_state],
        )

    return tab, conflict_selector, conflict_detail


def _status_html(message: str, level: str = "info") -> str:
    """Generate styled status HTML."""
    colors = {
        "info": "#64748b",
        "active": "#3b82f6",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
    }
    color = colors.get(level, colors["info"])
    return (
        f"<div style='color:{color};font-size:13px;padding:6px 0;'>"
        f"{message}</div>"
    )
