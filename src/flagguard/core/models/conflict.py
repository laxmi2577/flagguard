"""Conflict and issue models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class ConflictSeverity(Enum):
    """Severity level of a detected conflict.
    
    Used to prioritize which conflicts need immediate attention:
    - CRITICAL: Production will break, must fix before deploy
    - HIGH: Significant issue, fix this sprint
    - MEDIUM: Should be addressed, schedule for backlog
    - LOW: Minor concern, track but not urgent
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConflictType(Enum):
    """Type of detected conflict/issue.
    
    Distinguishes between different kinds of configuration problems:
    - MUTUAL_EXCLUSION: Two flags enabled that are explicitly conflicting
    - DEPENDENCY_VIOLATION: Enabled flag requires a disabled flag
    - INVALID_STATE: Generic invalid state
    """
    MUTUAL_EXCLUSION = "mutual_exclusion"
    DEPENDENCY_VIOLATION = "dependency_violation"
    INVALID_STATE = "invalid_state"


@dataclass
class Conflict:
    """A detected flag conflict or issue.
    
    Represents an impossible or problematic combination of flag states
    discovered through analysis.
    
    Attributes:
        conflict_id: Unique identifier for this conflict (e.g., "C001")
        flags_involved: List of flags that create the conflict
        conflicting_values: The impossible state (flag -> required value)
        severity: How serious this conflict is
        conflict_type: Type of issue (mutual exclusion vs dependency)
        reason: Technical explanation of why this conflicts
        affected_code_locations: File:line locations affected
        llm_explanation: Human-readable explanation from LLM
    """
    conflict_id: str
    flags_involved: List[str]
    conflicting_values: dict[str, bool]
    severity: ConflictSeverity
    reason: str
    conflict_type: ConflictType = ConflictType.MUTUAL_EXCLUSION
    affected_code_locations: List[str] = field(default_factory=list)
    llm_explanation: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.conflict_id,
            # Backwards compatibility: type field
            "type": self.conflict_type.value,
            "flags_involved": self.flags_involved,
            "conflicting_values": self.conflicting_values,
            "severity": self.severity.value,
            "reason": self.reason,
            "affected_locations": self.affected_code_locations,
            "explanation": self.llm_explanation,
        }


@dataclass
class DeadCodeBlock:
    """A block of unreachable code due to impossible flag states.
    
    Identifies code that can never execute because the required
    flag combination is mathematically impossible.
    
    Attributes:
        file_path: Path to the file containing dead code
        start_line: First line of the dead block
        end_line: Last line of the dead block
        required_flags: Flag states needed to reach this code
        reason: Explanation of why the code is unreachable
        code_snippet: The actual dead code content
    """
    file_path: str
    start_line: int
    end_line: int
    required_flags: dict[str, bool]
    reason: str
    code_snippet: str = ""

    @property
    def estimated_lines(self) -> int:
        """Calculate estimated lines of dead code."""
        return self.end_line - self.start_line + 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "required_flags": self.required_flags,
            "reason": self.reason,
            "estimated_lines": self.estimated_lines,
        }