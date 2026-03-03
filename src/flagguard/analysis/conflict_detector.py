"""Conflict detection using SAT solving.

Identifies impossible flag combinations and dependency violations.
"""

import uuid
from typing import TYPE_CHECKING

from flagguard.core.models import Conflict, ConflictSeverity, ConflictType, FlagDefinition
from flagguard.core.logging import get_logger

if TYPE_CHECKING:
    from flagguard.analysis.z3_wrapper import FlagSATSolver

logger = get_logger("conflict_detector")


class ConflictDetector:
    """Detects conflicts in feature flag configurations.
    
    Uses SAT solving to find impossible flag states based on:
    - Explicit dependencies from configuration
    - Mutual exclusion rules
    - Always-on/off constraints
    
    Attributes:
        solver: The FlagSATSolver instance
    """
    
    def __init__(self, solver: "FlagSATSolver") -> None:
        """Initialize the detector.
        
        Args:
            solver: Configured FlagSATSolver with constraints
        """
        self.solver = solver
        self._conflicts: list[Conflict] = []
        self._loaded_flags: list[FlagDefinition] = []
    
    def load_flags(self, flags: list[FlagDefinition]) -> None:
        """Load flag definitions and encode constraints.
        
        Args:
            flags: List of flag definitions to analyze
        """
        self._loaded_flags = flags
        for flag in flags:
            # Register the flag
            self.solver.get_or_create_var(flag.name)
            
            # Add enabled/disabled constraint
            # NOTE: We DO NOT force the current value here as a constraint,
            # because we want to check if the current value *violates* the rules.
            # If we forced it, the solver would just be UNSAT for the whole system
            # and we couldn't isolate the specific conflict.
            # We ONLY add "Infrastructure Constraints" (like dependencies).
            
            # Add dependency constraints
            for dep in flag.dependencies:
                self.solver.add_requires(flag.name, dep)
            
            # Add conflict constraints (Mutual Exclusion)
            for conflict_flag in flag.conflicts:
                self.solver.add_conflicts(flag.name, conflict_flag)

            logger.debug(f"Loaded flag: {flag.name} (enabled={flag.enabled})")

    def detect_all_conflicts(
        self,
        max_flags_per_conflict: int = 2,
    ) -> list[Conflict]:
        """Detect conflicts in the CURRENT configuration.
        
        Verifies that the currently enabled/disabled states of flags
        do not violate any constraints.
        
        Args:
            max_flags_per_conflict: Max flags to combine per check (default 2)
            
        Returns:
            List of detected conflicts/issues
        """
        self._conflicts.clear()
        
        # Create lookup map
        flags_map = {f.name: f for f in self._loaded_flags}
        
        # 1. Check for Dependency Violations
        # Rule: If Flag A is Enabled, and Flag A depends on Flag B, then Flag B must be Enabled.
        for flag in self._loaded_flags:
            if not flag.enabled:
                continue
                
            for dep_name in flag.dependencies:
                dep_flag = flags_map.get(dep_name)
                # If dependency doesn't exist or is disabled -> Violation
                if not dep_flag or not dep_flag.enabled:
                    state = {
                        flag.name: True,
                        dep_name: False  # The problematic state
                    }
                    
                    self._conflicts.append(Conflict(
                        conflict_id=f"D{uuid.uuid4().hex[:6].upper()}",
                        flags_involved=[flag.name, dep_name],
                        conflicting_values=state,
                        severity=ConflictSeverity.HIGH,
                        conflict_type=ConflictType.DEPENDENCY_VIOLATION,
                        reason=f"Flag '{flag.name}' is enabled but depends on '{dep_name}' which is disabled or missing."
                    ))

        # 2. Check for Mutual Exclusion Conflicts
        # Rule: If Flag A matches Flag B in conflict list, they cannot BOTH be Enabled.
        checked_pairs = set()
        
        for flag in self._loaded_flags:
            if not flag.enabled:
                continue
                
            for conflict_name in flag.conflicts:
                conflict_flag = flags_map.get(conflict_name)
                
                if conflict_flag and conflict_flag.enabled:
                    # Prevent reporting (A, B) and (B, A) twice
                    pair_key = frozenset([flag.name, conflict_name])
                    if pair_key in checked_pairs:
                        continue
                    checked_pairs.add(pair_key)
                    
                    state = {
                        flag.name: True,
                        conflict_name: True
                    }
                    
                    self._conflicts.append(Conflict(
                        conflict_id=f"C{uuid.uuid4().hex[:6].upper()}",
                        flags_involved=[flag.name, conflict_name],
                        conflicting_values=state,
                        severity=ConflictSeverity.CRITICAL,
                        conflict_type=ConflictType.MUTUAL_EXCLUSION,
                        reason=f"Flags '{flag.name}' and '{conflict_name}' are both enabled but are mutually exclusive."
                    ))
        
        logger.info(f"Detected {len(self._conflicts)} issues")
        return self._conflicts
    
    def _create_conflict(self, state: dict[str, bool]) -> Conflict:
        """Create a Conflict object from an impossible state."""
        flags = list(state.keys())
        
        # Determine severity based on flag states
        # If trying to enable flags that conflict, it's more severe
        if all(state.values()):
            severity = ConflictSeverity.CRITICAL
        elif any(state.values()):
            severity = ConflictSeverity.HIGH
        else:
            severity = ConflictSeverity.MEDIUM
        
        # Generate reason
        enabled_flags = [f for f, v in state.items() if v]
        disabled_flags = [f for f, v in state.items() if not v]
        
        if enabled_flags and disabled_flags:
            reason = (
                f"Enabling {', '.join(enabled_flags)} requires "
                f"{', '.join(disabled_flags)} to be enabled"
            )
        else:
            reason = f"Flags {', '.join(flags)} cannot be in this state together"
        
        return Conflict(
            conflict_id=f"C{uuid.uuid4().hex[:6].upper()}",
            flags_involved=flags,
            conflicting_values=state,
            severity=severity,
            reason=reason,
        )
    
    def check_state(self, flag_states: dict[str, bool]) -> Conflict | None:
        """Check if a specific state is possible.
        
        Args:
            flag_states: The state to check
            
        Returns:
            Conflict object if impossible, None if possible
        """
        if self.solver.check_state_possible(flag_states):
            return None
        return self._create_conflict(flag_states)
    
    @property
    def conflicts(self) -> list[Conflict]:
        """Get the list of detected conflicts."""
        return self._conflicts.copy()
