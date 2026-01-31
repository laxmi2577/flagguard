"""Z3 SAT solver wrapper for flag constraint solving.

Provides a high-level interface for encoding flag relationships
and checking for impossible states.
"""

from typing import Any

from flagguard.core.logging import get_logger

logger = get_logger("z3_wrapper")

# Try to import Z3
try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    logger.warning("Z3 not available - SAT solving will be disabled")


class FlagSATSolver:
    """SAT solver for feature flag constraints.
    
    Uses Z3 to model flag relationships and detect:
    - Impossible flag combinations
    - Required dependencies
    - Mutual exclusions
    
    Attributes:
        is_available: Whether Z3 is available for solving
    """
    
    def __init__(self) -> None:
        """Initialize the solver."""
        self._solver: Any = None
        self._variables: dict[str, Any] = {}
        self.is_available = Z3_AVAILABLE
        
        if Z3_AVAILABLE:
            self._solver = z3.Solver()
        else:
            logger.warning("SAT solver disabled - Z3 not installed")
    
    def reset(self) -> None:
        """Reset the solver state."""
        if self._solver:
            self._solver.reset()
        self._variables.clear()
    
    def get_or_create_var(self, flag_name: str) -> Any:
        """Get or create a boolean variable for a flag.
        
        Args:
            flag_name: Name of the flag
            
        Returns:
            Z3 boolean variable
        """
        if not Z3_AVAILABLE:
            return None
            
        if flag_name not in self._variables:
            self._variables[flag_name] = z3.Bool(flag_name)
        return self._variables[flag_name]
    
    def add_requires(self, flag: str, required_flag: str) -> None:
        """Add a dependency constraint: flag requires required_flag.
        
        If flag is True, then required_flag must be True.
        
        Args:
            flag: The dependent flag
            required_flag: The flag that is required
        """
        if not self._solver:
            return
            
        f = self.get_or_create_var(flag)
        r = self.get_or_create_var(required_flag)
        
        # flag => required_flag
        self._solver.add(z3.Implies(f, r))
        logger.debug(f"Added constraint: {flag} requires {required_flag}")
    
    def add_conflicts(self, flag1: str, flag2: str) -> None:
        """Add a mutual exclusion constraint.
        
        flag1 and flag2 cannot both be True.
        
        Args:
            flag1: First flag
            flag2: Second flag
        """
        if not self._solver:
            return
            
        f1 = self.get_or_create_var(flag1)
        f2 = self.get_or_create_var(flag2)
        
        # Not (flag1 AND flag2)
        self._solver.add(z3.Not(z3.And(f1, f2)))
        logger.debug(f"Added conflict: {flag1} conflicts with {flag2}")
    
    def add_always_on(self, flag: str) -> None:
        """Constrain a flag to always be True.
        
        Args:
            flag: The flag that must be enabled
        """
        if not self._solver:
            return
            
        f = self.get_or_create_var(flag)
        self._solver.add(f == True)
    
    def add_always_off(self, flag: str) -> None:
        """Constrain a flag to always be False.
        
        Args:
            flag: The flag that must be disabled
        """
        if not self._solver:
            return
            
        f = self.get_or_create_var(flag)
        self._solver.add(f == False)
    
    def check_state_possible(self, flag_states: dict[str, bool]) -> bool:
        """Check if a given flag state is satisfiable.
        
        Args:
            flag_states: Dictionary of flag -> desired value
            
        Returns:
            True if the state is possible, False if impossible
        """
        if not self._solver:
            # If no solver, assume all states are possible
            return True
        
        self._solver.push()
        
        try:
            for flag, value in flag_states.items():
                var = self.get_or_create_var(flag)
                self._solver.add(var == value)
            
            result = self._solver.check()
            return result == z3.sat
        finally:
            self._solver.pop()
    
    def get_impossible_states(
        self,
        flags: list[str],
        max_flags_per_state: int = 2,
    ) -> list[dict[str, bool]]:
        """Find impossible flag combinations.
        
        Enumerates combinations of flags and checks which are impossible.
        
        Args:
            flags: List of flag names to check
            max_flags_per_state: Maximum flags to combine per check
            
        Returns:
            List of impossible flag state dictionaries
        """
        if not self._solver:
            return []
        
        impossible: list[dict[str, bool]] = []
        
        # Check pairwise combinations
        for i, flag1 in enumerate(flags):
            for flag2 in flags[i + 1:]:
                # Check all four combinations
                for val1 in [True, False]:
                    for val2 in [True, False]:
                        state = {flag1: val1, flag2: val2}
                        if not self.check_state_possible(state):
                            impossible.append(state)
        
        return impossible
    
    @property
    def variables(self) -> list[str]:
        """Get list of all registered flag variables."""
        return list(self._variables.keys())
