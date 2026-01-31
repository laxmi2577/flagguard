"""Explanation engine that uses LLM to generate human-readable explanations."""

from typing import TYPE_CHECKING

from flagguard.core.models import Conflict, DeadCodeBlock
from flagguard.core.logging import get_logger
from flagguard.llm.prompts import (
    CONFLICT_EXPLANATION_PROMPT,
    DEAD_CODE_EXPLANATION_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
)

if TYPE_CHECKING:
    from flagguard.llm.ollama_client import OllamaClient

logger = get_logger("explainer")


class ExplanationEngine:
    """Generates human-readable explanations using LLM.
    
    Uses the configured LLM client to generate explanations
    for conflicts, dead code, and executive summaries.
    
    Attributes:
        client: The OllamaClient instance
        use_llm: Whether to use LLM (False for template-only fallback)
    """
    
    def __init__(
        self,
        client: "OllamaClient",
        use_llm: bool = True,
    ) -> None:
        """Initialize the engine.
        
        Args:
            client: Ollama client for LLM inference
            use_llm: Whether to use LLM or templates only
        """
        self.client = client
        self.use_llm = use_llm and client.is_available
    
    def explain_conflict(self, conflict: Conflict) -> str:
        """Generate an explanation for a conflict.
        
        Args:
            conflict: The conflict to explain
            
        Returns:
            Human-readable explanation
        """
        if not self.use_llm:
            return self._template_conflict_explanation(conflict)
        
        prompt = CONFLICT_EXPLANATION_PROMPT.format(
            flags=", ".join(conflict.flags_involved),
            values=", ".join(f"{k}={v}" for k, v in conflict.conflicting_values.items()),
            reason=conflict.reason,
        )
        
        explanation = self.client.generate(prompt)
        
        if not explanation or "[LLM unavailable]" in explanation:
            return self._template_conflict_explanation(conflict)
        
        return explanation.strip()
    
    def explain_dead_code(self, block: DeadCodeBlock) -> str:
        """Generate an explanation for dead code.
        
        Args:
            block: The dead code block to explain
            
        Returns:
            Human-readable explanation
        """
        if not self.use_llm:
            return self._template_dead_code_explanation(block)
        
        prompt = DEAD_CODE_EXPLANATION_PROMPT.format(
            file_path=block.file_path,
            start_line=block.start_line,
            end_line=block.end_line,
            flags=", ".join(f"{k}={v}" for k, v in block.required_flags.items()),
            code=block.code_snippet[:200] if block.code_snippet else "N/A",
        )
        
        explanation = self.client.generate(prompt)
        
        if not explanation or "[LLM unavailable]" in explanation:
            return self._template_dead_code_explanation(block)
        
        return explanation.strip()
    
    def generate_executive_summary(
        self,
        flag_count: int,
        conflicts: list[Conflict],
        dead_blocks: list[DeadCodeBlock],
    ) -> str:
        """Generate an executive summary of the analysis.
        
        Args:
            flag_count: Total number of flags analyzed
            conflicts: List of detected conflicts
            dead_blocks: List of dead code blocks
            
        Returns:
            Executive summary text
        """
        dead_lines = sum(b.estimated_lines for b in dead_blocks)
        
        if not self.use_llm:
            return self._template_executive_summary(
                flag_count, len(conflicts), len(dead_blocks), dead_lines
            )
        
        # Format top issues
        top_issues = []
        for c in conflicts[:3]:
            top_issues.append(f"- Conflict: {c.reason}")
        for b in dead_blocks[:2]:
            top_issues.append(f"- Dead code: {b.file_path}:{b.start_line}")
        
        prompt = EXECUTIVE_SUMMARY_PROMPT.format(
            flag_count=flag_count,
            conflict_count=len(conflicts),
            dead_code_count=len(dead_blocks),
            dead_lines=dead_lines,
            top_issues="\n".join(top_issues) or "No critical issues",
        )
        
        summary = self.client.generate(prompt)
        
        if not summary or "[LLM unavailable]" in summary:
            return self._template_executive_summary(
                flag_count, len(conflicts), len(dead_blocks), dead_lines
            )
        
        return summary.strip()
    
    def _template_conflict_explanation(self, conflict: Conflict) -> str:
        """Generate template-based conflict explanation."""
        flags_str = " and ".join(conflict.flags_involved)
        values_str = ", ".join(
            f"{'enabling' if v else 'disabling'} {k}"
            for k, v in conflict.conflicting_values.items()
        )
        
        return (
            f"The flags {flags_str} have a conflict. "
            f"The combination of {values_str} is not possible "
            f"due to dependency constraints. "
            f"Review the flag configuration to resolve this issue."
        )
    
    def _template_dead_code_explanation(self, block: DeadCodeBlock) -> str:
        """Generate template-based dead code explanation."""
        flags_str = ", ".join(
            f"{k}={'enabled' if v else 'disabled'}"
            for k, v in block.required_flags.items()
        )
        
        return (
            f"Code at {block.file_path}:{block.start_line}-{block.end_line} "
            f"(~{block.estimated_lines} lines) cannot execute. "
            f"It requires {flags_str}, which is impossible. "
            f"Consider removing this code or updating flag configuration."
        )
    
    def _template_executive_summary(
        self,
        flag_count: int,
        conflict_count: int,
        dead_code_count: int,
        dead_lines: int,
    ) -> str:
        """Generate template-based executive summary."""
        if conflict_count == 0 and dead_code_count == 0:
            return (
                f"Analysis of {flag_count} feature flags completed. "
                f"No conflicts or dead code detected. "
                f"Your flag configuration is healthy."
            )
        
        severity = "critical" if conflict_count > 5 else "moderate"
        
        return (
            f"Analysis of {flag_count} feature flags found {severity} issues: "
            f"{conflict_count} conflicts and {dead_code_count} dead code blocks "
            f"(~{dead_lines} lines). "
            f"Recommend prioritizing conflict resolution and scheduling "
            f"dead code cleanup."
        )
