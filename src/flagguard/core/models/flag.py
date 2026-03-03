"""Feature flag models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List


class FlagType(Enum):
    """Type of feature flag value."""
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


@dataclass
class FlagVariation:
    """A possible value for a feature flag."""
    name: str
    value: Any
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "description": self.description,
        }


@dataclass
class TargetingRule:
    """A rule that controls when a flag variation is served."""
    name: str
    conditions: List[dict[str, Any]]
    variation: str
    rollout_percentage: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "conditions": self.conditions,
            "variation": self.variation,
            "rollout_percentage": self.rollout_percentage,
        }


@dataclass
class FlagDefinition:
    """A complete feature flag definition."""
    name: str
    flag_type: FlagType
    enabled: bool
    default_variation: str = ""
    variations: List[FlagVariation] = field(default_factory=list)
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Backwards compatibility helper
    @property
    def requires(self):
        return self.dependencies

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Flag name cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.flag_type.value,
            "enabled": self.enabled,
            "default_variation": self.default_variation,
            "variations": [v.to_dict() for v in self.variations],
            "targeting_rules": [r.to_dict() for r in self.targeting_rules],
            "dependencies": self.dependencies,
            "conflicts": self.conflicts,
            "description": self.description,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlagDefinition":
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
            conflicts=data.get("conflicts", []),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )


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

