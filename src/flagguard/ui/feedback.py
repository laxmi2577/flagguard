"""Feedback Telemetry UI Component (Phase 3 — Step 3.3).

Provides a reusable Gradio component that adds 👍/👎 feedback buttons
below any LLM output. Stores feedback in SQLAlchemy for DPO training.

Usage:
    from flagguard.ui.feedback import create_feedback_component

    # In your Gradio tab:
    with gr.Row():
        output_text = gr.Markdown()
    feedback_html, feedback_state = create_feedback_component(
        output_ref=output_text,
        context_type="explanation",
    )
"""

import gradio as gr
from flagguard.core.logging import get_logger

logger = get_logger("ui.feedback")


def store_feedback(
    prompt: str,
    response: str,
    feedback: str,
    context_type: str = "explanation",
    conflict_id: str | None = None,
    user_id: str | None = None,
):
    """Store user feedback in the database.

    Args:
        prompt: The user's input/question.
        response: The LLM's output that was rated.
        feedback: "positive" or "negative".
        context_type: Type of output (explanation, fix, risk, chat).
        conflict_id: Optional conflict ID for context.
        user_id: Optional user ID.

    Returns:
        True if stored successfully, False otherwise.
    """
    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import LLMFeedback

        db = SessionLocal()
        try:
            entry = LLMFeedback(
                user_id=user_id,
                prompt=prompt,
                response=response,
                feedback=feedback,
                context_type=context_type,
                conflict_id=conflict_id,
                metadata_={"source": "gradio_ui"},
            )
            db.add(entry)
            db.commit()
            logger.info(f"Feedback stored: {feedback} for {context_type}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store feedback: {e}")
            return False
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Database unavailable for feedback: {e}")
        return False


def create_feedback_component(context_type: str = "explanation"):
    """Create a 👍/👎 feedback component for a Gradio tab.

    Args:
        context_type: The type of LLM output (explanation, fix, risk, chat).

    Returns:
        Tuple of (feedback_html, prompt_state, response_state).
    """
    # Hidden states to store the current prompt/response
    prompt_state = gr.State("")
    response_state = gr.State("")

    with gr.Row():
        gr.HTML(
            "<div style='display:flex;align-items:center;gap:8px;"
            "padding:8px 0;border-top:1px solid rgba(212,175,55,0.1);"
            "margin-top:8px;'>"
            "<span style='color:#64748b;font-size:12px;'>Was this helpful?</span>"
            "</div>"
        )
        thumbs_up = gr.Button(
            "👍", elem_classes=["feedback-btn"], scale=0, min_width=50
        )
        thumbs_down = gr.Button(
            "👎", elem_classes=["feedback-btn"], scale=0, min_width=50
        )
        feedback_status = gr.HTML("")

    def handle_feedback(feedback_type, prompt, response):
        """Handle a feedback button click."""
        if not prompt or not response:
            return "<span style='color:#f59e0b;font-size:12px;'>⚠️ No output to rate</span>"

        success = store_feedback(
            prompt=prompt,
            response=response,
            feedback=feedback_type,
            context_type=context_type,
        )

        if success:
            icon = "👍" if feedback_type == "positive" else "👎"
            return (
                f"<span style='color:#22c55e;font-size:12px;'>"
                f"✅ {icon} Feedback recorded! Helps improve FlagGuard AI.</span>"
            )
        return "<span style='color:#ef4444;font-size:12px;'>❌ Failed to save</span>"

    thumbs_up.click(
        fn=lambda p, r: handle_feedback("positive", p, r),
        inputs=[prompt_state, response_state],
        outputs=[feedback_status],
    )
    thumbs_down.click(
        fn=lambda p, r: handle_feedback("negative", p, r),
        inputs=[prompt_state, response_state],
        outputs=[feedback_status],
    )

    return feedback_status, prompt_state, response_state
