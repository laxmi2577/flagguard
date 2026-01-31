"""Encode flag configurations as SAT constraints.

Converts flag definitions and usage patterns into constraints 
that can be analyzed by the SAT solver.
"""

from typing import Any

from flagguard.core.models import FlagDefinition, FlagUsage
from flagguard.analysis.z3_wrapper import FlagSATSolver
from flagguard.core.logging import get_logger

logger = get_logger("constraint_encoder")


class ConstraintEncoder:
    """Encodes flag relationships as SAT constraints.
    
    This class takes flag definitions from configuration files
    and source code usage patterns, then converts them into
    constraints suitable for SAT solving.
    
    Attributes:
        solver: The FlagSATSolver instance with encoded constraints
    """
    
    def __init__(self, solver: FlagSATSolver | None = None) -> None:
        """Initialize the encoder.
        
        Args:
            solver: Optional existing solver. If None, creates a new one.
        """
        self.solver = solver or FlagSATSolver()
    
    def encode_flags(self, flags: list[FlagDefinition]) -> FlagSATSolver:
        """Encode flag definitions into solver constraints.
        
        Processes each flag and encodes:
        - The flag as a boolean variable
        - Disabled flags as always-off constraints  
        - Dependencies as implication constraints
        
        Args:
            flags: List of flag definitions to encode
            
        Returns:
            The solver instance with constraints added
        """
        for flag in flags:
            # Register the flag as a variable
            self.solver.get_or_create_var(flag.name)
            
            # If flag is disabled, add always-off constraint
            if not flag.enabled:
                self.solver.add_always_off(flag.name)
                logger.debug(f"Encoded {flag.name} as always-off")
            
            # Encode dependencies (flag -> dependency)
            for dep in flag.dependencies:
                self.solver.add_requires(flag.name, dep)
                logger.debug(f"Encoded dependency: {flag.name} requires {dep}")
        
        logger.info(f"Encoded {len(flags)} flags into constraints")
        return self.solver
    
    def encode_usage_constraints(
        self,
        usages: list[FlagUsage],
        flags: list[FlagDefinition],
    ) -> None:
        """Encode constraints derived from code usage patterns.
        
        Analyzes how flags are used in code to infer additional constraints
        such as implicit dependencies from nested checks.
        
        Args:
            usages: List of flag usages found in code
            flags: List of declared flag definitions
        """
        declared_flags = {f.name for f in flags}
        
        for usage in usages:
            # Create variable for undeclared flags (used in code but not in config)
            if usage.flag_name not in declared_flags:
                self.solver.get_or_create_var(usage.flag_name)
                logger.warning(f"Found undeclared flag in code: {usage.flag_name}")
        
        # Infer additional constraints from usage patterns
        self._infer_constraints_from_usage(usages)
    
    def _infer_constraints_from_usage(self, usages: list[FlagUsage]) -> None:
        """Infer constraints from code patterns.
        
        Looks for patterns like nested flag checks that suggest
        implicit dependencies between flags.
        
        Args:
            usages: List of FlagUsage instances to analyze
        """
        # Group usages by containing function
        by_function: dict[str, list[FlagUsage]] = {}
        for u in usages:
            key = f"{u.file_path}:{u.containing_function or 'global'}"
            by_function.setdefault(key, []).append(u)
        
        # Look for nested checks indicating potential dependencies
        for location, location_usages in by_function.items():
            if len(location_usages) >= 2:
                # Sort by line number to understand nesting
                sorted_usages = sorted(location_usages, key=lambda u: u.line_number)
                
                # If flags are checked in sequence in same function,
                # they might be related (this is a heuristic)
                for i in range(len(sorted_usages) - 1):
                    outer = sorted_usages[i]
                    inner = sorted_usages[i + 1]
                    
                    # If inner check is within outer's scope (rough heuristic)
                    if inner.line_number > outer.line_number:
                        # Potential inference: inner may depend on outer
                        logger.debug(
                            f"Potential dependency: {inner.flag_name} may require "
                            f"{outer.flag_name} at {location}"
                        )
    
    def encode_exclusive_flags(self, groups: list[list[str]]) -> None:
        """Encode groups of mutually exclusive flags.
        
        Only one flag in each group can be enabled at a time.
        
        Args:
            groups: List of groups, each group is a list of mutually exclusive flags
        """
        for group in groups:
            if len(group) < 2:
                continue
            
            # Add pairwise conflicts
            for i, flag1 in enumerate(group):
                for flag2 in group[i + 1:]:
                    self.solver.add_conflicts(flag1, flag2)
            
            logger.debug(f"Encoded mutual exclusion group: {group}")
    
    def encode_required_flags(self, flags: list[str]) -> None:
        """Encode flags that must always be enabled.
        
        These are production-critical flags that should never be disabled.
        
        Args:
            flags: List of flag names that must be enabled
        """
        for flag in flags:
            self.solver.add_always_on(flag)
            logger.debug(f"Encoded {flag} as required (always-on)")
    
    def encode_disabled_flags(self, flags: list[str]) -> None:
        """Encode flags that must always be disabled.
        
        These might be deprecated flags or features not yet ready.
        
        Args:
            flags: List of flag names that must be disabled
        """
        for flag in flags:
            self.solver.add_always_off(flag)
            logger.debug(f"Encoded {flag} as disabled (always-off)")
    
    def encode_from_config_states(self, states: dict[str, bool]) -> None:
        """Encode the current configuration state.
        
        Takes the current flag configuration (what's deployed) and 
        encodes it as constraints for analysis.
        
        Args:
            states: Dictionary mapping flag names to their current state
        """
        for flag, is_enabled in states.items():
            if is_enabled:
                self.solver.add_always_on(flag)
            else:
                self.solver.add_always_off(flag)
