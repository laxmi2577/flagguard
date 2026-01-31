"""Analysis module for flag conflict detection.

This module provides SAT-based analysis for detecting:
- Flag conflicts (impossible states)
- Dead code (unreachable due to flag configurations)
- Dependency relationships
- Code path analysis
"""

from flagguard.analysis.z3_wrapper import FlagSATSolver
from flagguard.analysis.conflict_detector import ConflictDetector
from flagguard.analysis.dead_code import DeadCodeFinder
from flagguard.analysis.path_analyzer import PathAnalyzer, CodePath
from flagguard.analysis.constraint_encoder import ConstraintEncoder

__all__ = [
    "FlagSATSolver",
    "ConflictDetector",
    "DeadCodeFinder",
    "PathAnalyzer",
    "CodePath",
    "ConstraintEncoder",
]


