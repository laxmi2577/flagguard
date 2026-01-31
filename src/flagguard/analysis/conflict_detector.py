"""Conflict detection using SAT solving.

Identifies impossible flag combinations and dependency violations.
"""

import uuid
from typing import TYPE_CHECKING

from flagguard.core.models import Conflict, ConflictSeverity, FlagDefinition
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
    
    def load_flags(self, flags: list[FlagDefinition]) -> None:
        """Load flag definitions and encode constraints.
        
        Args:
            flags: List of flag definitions to analyze
        """
        for flag in flags:
            # Register the flag
            self.solver.get_or_create_var(flag.name)
            
            # Add enabled/disabled constraint
            if not flag.enabled:
                self.solver.add_always_off(flag.name)
            
            # Add dependency constraints
            for dep in flag.dependencies:
                self.solver.add_requires(flag.name, dep)
            
            logger.debug(f"Loaded flag: {flag.name} (enabled={flag.enabled})")
    
    def detect_all_conflicts(
        self,
        max_flags_per_conflict: int = 2,
    ) -> list[Conflict]:
        """Detect all conflicts in the loaded flags.
        
        Args:
            max_flags_per_conflict: Max flags to combine per check
            
        Returns:
            List of detected conflicts
        """
        self._conflicts.clear()
        
        # Get impossible states
        impossible_states = self.solver.get_impossible_states(
            self.solver.variables,
            max_flags_per_conflict,
        )
        
        for state in impossible_states:
            conflict = self._create_conflict(state)
            self._conflicts.append(conflict)
        
        logger.info(f"Detected {len(self._conflicts)} conflicts")
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
