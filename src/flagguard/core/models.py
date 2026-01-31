"""Core data models for FlagGuard.

This module defines the fundamental data structures used throughout FlagGuard
for representing feature flags, their usage in code, and analysis results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FlagType(Enum):
    """Type of feature flag value.
    
    Feature flags can hold different types of values:
    - BOOLEAN: Simple on/off toggle (most common)
    - STRING: Text-based variations for A/B testing
    - NUMBER: Numeric values for gradual rollouts
    - JSON: Complex structured data
    """
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


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


@dataclass
class FlagVariation:
    """A possible value for a feature flag.
    
    Represents one of the possible states a flag can be in.
    For boolean flags, typically "on" and "off".
    For multivariate flags, can be multiple named variations.
    
    Attributes:
        name: Identifier for this variation (e.g., "on", "off", "variant_a")
        value: The actual value returned when this variation is served
        description: Human-readable explanation of this variation
    """
    name: str
    value: Any
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "value": self.value,
            "description": self.description,
        }


@dataclass
class TargetingRule:
    """A rule that controls when a flag variation is served.
    
    Targeting rules define which users/contexts receive which variation.
    They are evaluated in order until one matches.
    
    Attributes:
        name: Identifier for this rule
        conditions: List of conditions that must be met (AND logic)
        variation: Which variation to serve when conditions match
        rollout_percentage: Percentage of matching users who get this variation
    """
    name: str
    conditions: list[dict[str, Any]]
    variation: str
    rollout_percentage: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "conditions": self.conditions,
            "variation": self.variation,
            "rollout_percentage": self.rollout_percentage,
        }


@dataclass
class FlagDefinition:
    """A complete feature flag definition.
    
    Represents a flag as defined in the configuration, including
    all its variations, targeting rules, and relationships to other flags.
    
    Attributes:
        name: Unique identifier for this flag (flag key)
        flag_type: The type of value this flag holds
        enabled: Whether the flag is globally enabled
        default_variation: Variation served when no rules match
        variations: All possible values for this flag
        targeting_rules: Rules controlling who gets which variation
        dependencies: Other flags that must be enabled for this to work
        description: Human-readable explanation of flag purpose
        tags: Labels for categorization and filtering
    """
    name: str
    flag_type: FlagType
    enabled: bool
    default_variation: str = ""
    variations: list[FlagVariation] = field(default_factory=list)
    targeting_rules: list[TargetingRule] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate flag definition after initialization."""
        if not self.name:
            raise ValueError("Flag name cannot be empty")
        if not self.name.replace("_", "").replace("-", "").replace(".", "").isalnum():
            # Allow alphanumeric, underscore, hyphen, and dot
            pass  # Just a warning, don't reject

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "type": self.flag_type.value,
            "enabled": self.enabled,
            "default_variation": self.default_variation,
            "variations": [v.to_dict() for v in self.variations],
            "targeting_rules": [r.to_dict() for r in self.targeting_rules],
            "dependencies": self.dependencies,
            "description": self.description,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlagDefinition":
        """Create FlagDefinition from dictionary."""
        variations = [
            FlagVariation(**v) if isinstance(v, dict) else v
            for v in data.get("variations", [])
        ]
        targeting_rules = [
            TargetingRule(**r) if isinstance(r, dict) else r
            for r in data.get("targeting_rules", [])
        ]
        return cls(
            name=data["name"],
            flag_type=FlagType(data.get("type", "boolean")),
            enabled=data.get("enabled", True),
            default_variation=data.get("default_variation", ""),
            variations=variations,
            targeting_rules=targeting_rules,
            dependencies=data.get("dependencies", []),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )


@dataclass
class FlagUsage:
    """A location where a feature flag is checked in source code.
    
    Tracks each occurrence of a flag check in the codebase,
    capturing context about where and how the flag is used.
    
    Attributes:
        flag_name: The flag being checked
        file_path: Absolute path to the source file
        line_number: Line number where the check occurs (1-indexed)
        column: Column number where the check starts (0-indexed)
        end_line: Line where the check expression ends
        end_column: Column where the check expression ends
        containing_function: Name of the function containing this check
        containing_class: Name of the class containing this check
        check_type: Type of check ("if", "ternary", "switch", "assignment")
        negated: True if checking for flag being OFF (!is_enabled)
        code_snippet: The actual code at this location
    """
    flag_name: str
    file_path: str
    line_number: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0
    containing_function: str | None = None
    containing_class: str | None = None
    check_type: str = "if"
    negated: bool = False
    code_snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "flag_name": self.flag_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "containing_function": self.containing_function,
            "containing_class": self.containing_class,
            "check_type": self.check_type,
            "negated": self.negated,
            "code_snippet": self.code_snippet,
        }

    @property
    def location(self) -> str:
        """Return formatted location string."""
        return f"{self.file_path}:{self.line_number}"


@dataclass
class FlagUsageDatabase:
    """Collection of all flag usages in a codebase.
    
    Aggregates all detected flag usages with metadata about
    the scanning process.
    
    Attributes:
        usages: List of all detected flag usages
        files_scanned: Number of source files processed
        scan_time_seconds: Time taken to complete the scan
        errors: Any parsing errors encountered
    """
    usages: list[FlagUsage]
    files_scanned: int
    scan_time_seconds: float
    errors: list[str] = field(default_factory=list)

    def get_by_flag(self, flag_name: str) -> list[FlagUsage]:
        """Get all usages of a specific flag."""
        return [u for u in self.usages if u.flag_name == flag_name]

    def get_by_file(self, file_path: str) -> list[FlagUsage]:
        """Get all flag usages in a specific file."""
        return [u for u in self.usages if u.file_path == file_path]

    def get_unique_flags(self) -> set[str]:
        """Get set of all unique flag names found."""
        return {u.flag_name for u in self.usages}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "usages": [u.to_dict() for u in self.usages],
            "files_scanned": self.files_scanned,
            "scan_time_seconds": self.scan_time_seconds,
            "unique_flags": list(self.get_unique_flags()),
            "errors": self.errors,
        }


@dataclass
class Conflict:
    """A detected flag conflict.
    
    Represents an impossible or problematic combination of flag states
    discovered through SAT solving analysis.
    
    Attributes:
        conflict_id: Unique identifier for this conflict (e.g., "C001")
        flags_involved: List of flags that create the conflict
        conflicting_values: The impossible state (flag -> required value)
        severity: How serious this conflict is
        reason: Technical explanation of why this conflicts
        affected_code_locations: File:line locations affected
        llm_explanation: Human-readable explanation from LLM
    """
    conflict_id: str
    flags_involved: list[str]
    conflicting_values: dict[str, bool]
    severity: ConflictSeverity
    reason: str
    affected_code_locations: list[str] = field(default_factory=list)
    llm_explanation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.conflict_id,
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


@dataclass
class FlagDependency:
    """A dependency relationship between flags.
    
    Represents how one flag relates to another, either explicitly
    from configuration or inferred from code usage.
    
    Attributes:
        source_flag: The flag that has the dependency
        target_flag: The flag it depends on
        dependency_type: Type of relationship ("requires", "conflicts_with", "implies")
        source: Where this was detected ("explicit" from config, "inferred" from code)
    """
    source_flag: str
    target_flag: str
    dependency_type: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source": self.source_flag,
            "target": self.target_flag,
            "type": self.dependency_type,
            "source_type": self.source,
        }
