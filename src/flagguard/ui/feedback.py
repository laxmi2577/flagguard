"""Feedback Telemetry UI Component (Phase 3 — Step 3.3).

Provides a production-grade, reusable Gradio component for collecting
👍/👎 preference signals on LLM outputs. These signals feed the DPO
(Direct Preference Optimization) alignment pipeline.

Architecture:
    - Feedback is stored atomically in SQLAlchemy using a context-managed session
    - Rate limiting per session_hash prevents double-submission spam
    - Graceful degradation: feedback always attempts to write, but UI never
      fails or blocks the user if the DB is unavailable
    - The component is fully decoupled from Gradio layout — it only returns
      Gradio State objects and registers button click handlers

Usage:
    from flagguard.ui.feedback import create_feedback_component

    # In any Gradio tab:
    with gr.Blocks():
        output_box = gr.Markdown()

        # Wire component — returns state refs for your event handlers to populate
        status_html, prompt_state, response_state = create_feedback_component(
            context_type="fix",
        )

        # After your LLM call, update the states so feedback knows what to rate:
        generate_btn.click(
            fn=my_llm_fn,
            inputs=[...],
            outputs=[output_box, prompt_state, response_state],
        )
"""

from __future__ import annotations

import hashlib
import time
from typing import Final

import gradio as gr

from flagguard.core.logging import get_logger

log = get_logger("ui.feedback")

# In-memory rate limit: hash → last_submission_unix_ts
_rate_limit_cache: dict[str, float] = {}
_RATE_LIMIT_SECONDS: Final[int] = 5


# ── DB persistence ────────────────────────────────────────────────────────────

def _compute_session_hash(prompt: str, response: str, feedback_type: str) -> str:
    """SHA-256 fingerprint of a specific feedback submission to detect duplicates."""
    payload = f"{prompt}|{response}|{feedback_type}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def store_feedback(
    prompt: str,
    response: str,
    feedback: str,
    context_type: str = "explanation",
    conflict_id: str | None = None,
    user_id: str | None = None,
) -> tuple[bool, str]:
    """Persist a feedback record atomically.

    Uses an explicit SQLAlchemy session with try/except/rollback/close
    to guarantee no connection leaks even if the commit fails.

    Args:
        prompt: The user query / LLM input that was rated.
        response: The LLM output that was rated.
        feedback: "positive" or "negative".
        context_type: Output type — "explanation", "fix", "risk", or "chat".
        conflict_id: Optional reference to the flagguard conflict being discussed.
        user_id: Optional authenticated user ID.

    Returns:
        Tuple of (success: bool, error_message: str).
    """
    # Input validation
    if feedback not in ("positive", "negative"):
        return False, f"Invalid feedback value: {feedback!r}"
    if not prompt.strip() or not response.strip():
        return False, "Prompt or response is empty — nothing to rate."

    # Rate limiting
    session_hash = _compute_session_hash(prompt, response, feedback)
    now = time.monotonic()
    last = _rate_limit_cache.get(session_hash, 0.0)
    if now - last < _RATE_LIMIT_SECONDS:
        return False, "Feedback already recorded for this response."
    _rate_limit_cache[session_hash] = now

    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import LLMFeedback
    except ImportError as exc:
        log.error("DB import failed — feedback not stored: %s", exc)
        return False, "Database unavailable."

    db = SessionLocal()
    try:
        entry = LLMFeedback(
            user_id=user_id,
            prompt=prompt,
            response=response,
            feedback=feedback,
            context_type=context_type,
            conflict_id=conflict_id,
            metadata_={
                "source": "gradio_ui",
                "context_type": context_type,
                "session_hash": session_hash,
            },
        )
        db.add(entry)
        db.commit()
        log.info(
            "Feedback stored: %s | context=%s | hash=%s",
            feedback, context_type, session_hash,
        )
        return True, ""
    except Exception as exc:
        db.rollback()
        log.error("DB commit failed: %s", exc)
        return False, f"Failed to save: {exc}"
    finally:
        db.close()


# ── Gradio Component ──────────────────────────────────────────────────────────

def create_feedback_component(context_type: str = "explanation") -> tuple:
    """Render 👍/👎 buttons and wire feedback collection to the DB.

    Call this **inside** a `gr.Blocks()` or `gr.TabItem()` context.
    The returned state objects must be listed in the `outputs` of whatever
    event populates the LLM response — that's how the feedback component
    knows which prompt+response pair the user is rating.

    Args:
        context_type: Type label for the LLM output being rated.
            One of "explanation", "fix", "risk", "chat", "dependency".

    Returns:
        Tuple of:
            - feedback_status (gr.HTML): shows confirmation/error messages
            - prompt_state (gr.State): hidden state — write the user's prompt here
            - response_state (gr.State): hidden state — write the LLM response here
    """
    prompt_state = gr.State("")
    response_state = gr.State("")

    with gr.Row(elem_classes=["feedback-row"]):
        gr.HTML(
            "<div style='"
            "display:flex;align-items:center;gap:10px;"
            "padding:8px 0 4px 0;"
            "border-top:1px solid rgba(212,175,55,0.15);"
            "margin-top:12px;"
            "'>"
            "<span style='"
            "color:#64748b;font-size:12px;font-style:italic;"
            "'>Rate this response to improve FlagGuard AI:</span>"
            "</div>"
        )
        thumbs_up = gr.Button(
            "👍  Helpful",
            elem_id=f"feedback-up-{context_type}",
            scale=0,
            size="sm",
            variant="secondary",
        )
        thumbs_down = gr.Button(
            "👎  Not helpful",
            elem_id=f"feedback-down-{context_type}",
            scale=0,
            size="sm",
            variant="secondary",
        )
        feedback_status = gr.HTML("")

    def _handle(feedback_type: str, prompt: str, response: str) -> str:
        """Handle a feedback click — returns HTML status message."""
        if not prompt or not response:
            return (
                "<span style='color:#f59e0b;font-size:12px;'>"
                "⚠️ No LLM output loaded — generate a response first, then rate it."
                "</span>"
            )

        ok, err = store_feedback(
            prompt=prompt,
            response=response,
            feedback=feedback_type,
            context_type=context_type,
        )

        if ok:
            icon = "👍" if feedback_type == "positive" else "👎"
            colour = "#22c55e" if feedback_type == "positive" else "#f59e0b"
            return (
                f"<span style='color:{colour};font-size:12px;font-weight:500;'>"
                f"✅ {icon} Recorded — thank you! This trains FlagGuard-Coder."
                f"</span>"
            )

        if "already recorded" in err:
            return (
                "<span style='color:#64748b;font-size:12px;'>"
                "ℹ️ Feedback already saved for this response."
                "</span>"
            )

        return (
            f"<span style='color:#ef4444;font-size:12px;'>"
            f"❌ Could not save feedback: {err}"
            f"</span>"
        )

    thumbs_up.click(
        fn=lambda p, r: _handle("positive", p, r),
        inputs=[prompt_state, response_state],
        outputs=[feedback_status],
        api_name=False,
    )
    thumbs_down.click(
        fn=lambda p, r: _handle("negative", p, r),
        inputs=[prompt_state, response_state],
        outputs=[feedback_status],
        api_name=False,
    )

    return feedback_status, prompt_state, response_state
