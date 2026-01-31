"""Dead code detection using SAT solving.

Identifies code blocks that can never execute due to
impossible flag combinations.
"""

from typing import TYPE_CHECKING

from flagguard.core.models import DeadCodeBlock, FlagUsage
from flagguard.core.logging import get_logger

if TYPE_CHECKING:
    from flagguard.analysis.z3_wrapper import FlagSATSolver

logger = get_logger("dead_code")


class DeadCodeFinder:
    """Finds dead code blocks based on flag configurations.
    
    Analyzes code paths to find blocks that require impossible
    flag combinations to execute.
    
    Attributes:
        solver: The FlagSATSolver instance with constraints
    """
    
    def __init__(self, solver: "FlagSATSolver") -> None:
        """Initialize the finder.
        
        Args:
            solver: Configured FlagSATSolver with constraints
        """
        self.solver = solver
        self._dead_blocks: list[DeadCodeBlock] = []
    
    def find_dead_code(
        self,
        usages: list[FlagUsage],
    ) -> list[DeadCodeBlock]:
        """Find dead code blocks based on flag usages.
        
        Checks each flag usage to see if its required state
        is impossible.
        
        Args:
            usages: List of flag usages from source scanning
            
        Returns:
            List of dead code blocks
        """
        self._dead_blocks.clear()
        
        for usage in usages:
            dead_block = self._check_usage(usage)
            if dead_block:
                self._dead_blocks.append(dead_block)
        
        logger.info(f"Found {len(self._dead_blocks)} dead code blocks")
        return self._dead_blocks
    
    def _check_usage(self, usage: FlagUsage) -> DeadCodeBlock | None:
        """Check if a flag usage leads to dead code.
        
        Args:
            usage: The flag usage to check
            
        Returns:
            DeadCodeBlock if the code is dead, None otherwise
        """
        # Determine required state based on check type
        # If checking for flag=True but that's impossible, it's dead
        required_value = not usage.negated
        
        state = {usage.flag_name: required_value}
        
        if not self.solver.check_state_possible(state):
            return DeadCodeBlock(
                file_path=usage.file_path,
                start_line=usage.line_number,
                end_line=usage.end_line or usage.line_number,
                required_flags=state,
                reason=self._generate_reason(usage, required_value),
                code_snippet=usage.code_snippet,
            )
        
        return None
    
    def _generate_reason(self, usage: FlagUsage, required_value: bool) -> str:
        """Generate a human-readable reason for dead code."""
        if required_value:
            return (
                f"Code requires '{usage.flag_name}' to be enabled, "
                f"but it is always disabled"
            )
        else:
            return (
                f"Code requires '{usage.flag_name}' to be disabled, "
                f"but it is always enabled"
            )
    
    def check_path(
        self,
        path_conditions: dict[str, bool],
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> DeadCodeBlock | None:
        """Check if a code path with given conditions is dead.
        
        Args:
            path_conditions: Required flag states for this path
            file_path: Path to the source file
            start_line: Start line of the code block
            end_line: End line of the code block
            
        Returns:
            DeadCodeBlock if the path is dead, None otherwise
        """
        if not self.solver.check_state_possible(path_conditions):
            flags_desc = ", ".join(
                f"{f}={v}" for f, v in path_conditions.items()
            )
            return DeadCodeBlock(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                required_flags=path_conditions,
                reason=f"Path requires impossible state: {flags_desc}",
            )
        return None
    
    @property
    def dead_blocks(self) -> list[DeadCodeBlock]:
        """Get the list of found dead code blocks."""
        return self._dead_blocks.copy()
    
    @property
    def total_dead_lines(self) -> int:
        """Get the total number of dead lines found."""
        return sum(b.estimated_lines for b in self._dead_blocks)
