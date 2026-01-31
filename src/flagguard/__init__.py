"""FlagGuard: AI Feature Flag Conflict Analyzer.

A static analysis tool that detects conflicts, impossible states,
and dead code in feature flag configurations using SAT solving.
"""

__version__ = "0.1.0"
__author__ = "FlagGuard Team"

from flagguard.core.models import (
    Conflict,
    ConflictSeverity,
    DeadCodeBlock,
    FlagDefinition,
    FlagType,
    FlagUsage,
    FlagVariation,
    TargetingRule,
)

__all__ = [
    "Conflict",
    "ConflictSeverity",
    "DeadCodeBlock",
    "FlagDefinition",
    "FlagType",
    "FlagUsage",
    "FlagVariation",
    "TargetingRule",
    "__version__",
]
