"""Path analysis engine for tracing code paths and flag dependencies.

Combines flag definitions with flag usages to trace all possible code paths
under different flag combinations and builds a dependency graph.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from flagguard.core.models import (
    FlagDefinition,
    FlagUsage,
    FlagDependency,
)
from flagguard.core.logging import get_logger

logger = get_logger("path_analyzer")


@dataclass
class CodePath:
    """A code path with its flag requirements.
    
    Represents a block of code that executes under specific flag conditions.
    
    Attributes:
        start_line: First line of the code block
        end_line: Last line of the code block
        file_path: Path to the source file
        required_flags: Map of flag names to required boolean values
        containing_function: Name of the function containing this path
        code_snippet: The actual code in this path
    """
    start_line: int
    end_line: int
    file_path: str
    required_flags: dict[str, bool] = field(default_factory=dict)
    containing_function: str | None = None
    code_snippet: str = ""
    
    @property
    def line_count(self) -> int:
        """Number of lines in this code path."""
        return self.end_line - self.start_line + 1
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "required_flags": self.required_flags,
            "containing_function": self.containing_function,
            "line_count": self.line_count,
        }


class PathAnalyzer:
    """Analyzes code paths based on flag usages.
    
    Combines flag definitions and usages to:
    - Build code paths with flag requirements
    - Identify implicit dependencies between flags
    - Generate dependency graphs
    
    Attributes:
        flags: Dictionary of flag definitions by name
        usages: List of flag usages from source scanning
    """
    
    def __init__(
        self,
        flags: list[FlagDefinition],
        usages: list[FlagUsage],
    ) -> None:
        """Initialize the analyzer.
        
        Args:
            flags: List of flag definitions
            usages: List of flag usages from source scanning
        """
        self.flags = {f.name: f for f in flags}
        self.usages = usages
        self._paths: list[CodePath] = []
        self._dependencies: list[FlagDependency] = []
        self._graph: nx.DiGraph = nx.DiGraph()
    
    def analyze(self) -> None:
        """Run the full path analysis."""
        self._build_paths()
        self._infer_dependencies()
        self._build_graph()
        logger.info(
            f"Analyzed {len(self._paths)} code paths, "
            f"found {len(self._dependencies)} dependencies"
        )
    
    def _build_paths(self) -> None:
        """Build code paths from flag usages."""
        # Group usages by file and function
        paths_by_location: dict[tuple[str, str | None], list[FlagUsage]] = {}
        
        for usage in self.usages:
            key = (usage.file_path, usage.containing_function)
            if key not in paths_by_location:
                paths_by_location[key] = []
            paths_by_location[key].append(usage)
        
        # Create code paths
        for (file_path, func), usages in paths_by_location.items():
            if not usages:
                continue
            
            # Determine required flags for this path
            required_flags: dict[str, bool] = {}
            for usage in usages:
                required_flags[usage.flag_name] = not usage.negated
            
            # Get line range
            lines = [u.line_number for u in usages]
            start_line = min(lines)
            end_line = max(u.end_line or u.line_number for u in usages)
            
            self._paths.append(CodePath(
                start_line=start_line,
                end_line=end_line,
                file_path=file_path,
                required_flags=required_flags,
                containing_function=func,
            ))
    
    def _infer_dependencies(self) -> None:
        """Infer dependencies from flag definitions and code patterns."""
        # Add explicit dependencies from flag definitions
        for flag in self.flags.values():
            for dep in flag.dependencies:
                self._dependencies.append(FlagDependency(
                    source_flag=flag.name,
                    target_flag=dep,
                    dependency_type="requires",
                    source="explicit",
                ))
        
        # Infer dependencies from code co-occurrence
        # If two flags are always checked together, they may be related
        flag_cooccurrence: dict[tuple[str, str], int] = {}
        
        for path in self._paths:
            flags_in_path = list(path.required_flags.keys())
            for i, flag1 in enumerate(flags_in_path):
                for flag2 in flags_in_path[i + 1:]:
                    key = tuple(sorted([flag1, flag2]))  # type: ignore
                    flag_cooccurrence[key] = flag_cooccurrence.get(key, 0) + 1
        
        # Add frequent co-occurrences as implied dependencies
        for (flag1, flag2), count in flag_cooccurrence.items():
            if count >= 3:  # Threshold for "frequently together"
                self._dependencies.append(FlagDependency(
                    source_flag=flag1,
                    target_flag=flag2,
                    dependency_type="implies",
                    source="inferred",
                ))
    
    def _build_graph(self) -> None:
        """Build NetworkX dependency graph."""
        self._graph.clear()
        
        # Add nodes for all flags
        for flag in self.flags.values():
            self._graph.add_node(
                flag.name,
                enabled=flag.enabled,
                flag_type=flag.flag_type.value,
            )
        
        # Add edges for dependencies
        for dep in self._dependencies:
            self._graph.add_edge(
                dep.source_flag,
                dep.target_flag,
                dependency_type=dep.dependency_type,
                source=dep.source,
            )
    
    def get_mermaid_diagram(self) -> str:
        """Generate a Mermaid flowchart diagram.
        
        Returns:
            Mermaid diagram definition as string
        """
        lines = ["flowchart TD"]
        
        # Add nodes
        for node, attrs in self._graph.nodes(data=True):
            enabled = attrs.get("enabled", True)
            style = ":::enabled" if enabled else ":::disabled"
            lines.append(f"    {node}[{node}]{style}")
        
        # Add edges with labels
        for source, target, attrs in self._graph.edges(data=True):
            dep_type = attrs.get("dependency_type", "requires")
            if dep_type == "requires":
                lines.append(f"    {source} -->|requires| {target}")
            elif dep_type == "conflicts_with":
                lines.append(f"    {source} -.->|conflicts| {target}")
            elif dep_type == "implies":
                lines.append(f"    {source} -.->|often with| {target}")
            else:
                lines.append(f"    {source} --> {target}")
        
        # Add style definitions
        lines.extend([
            "",
            "    classDef enabled fill:#90EE90,stroke:#228B22",
            "    classDef disabled fill:#FFB6C1,stroke:#DC143C",
        ])
        
        return "\n".join(lines)
    
    def get_circular_dependencies(self) -> list[list[str]]:
        """Find circular dependencies in the flag graph.
        
        Returns:
            List of cycles (each cycle is a list of flag names)
        """
        try:
            cycles = list(nx.simple_cycles(self._graph))
            return cycles
        except nx.NetworkXNoCycle:
            return []
    
    def get_flags_affecting_file(self, file_path: str) -> set[str]:
        """Get all flags that affect code in a specific file.
        
        Args:
            file_path: Path to the source file
            
        Returns:
            Set of flag names used in the file
        """
        return {
            u.flag_name
            for u in self.usages
            if u.file_path == file_path
        }
    
    def get_files_affected_by_flag(self, flag_name: str) -> set[str]:
        """Get all files that check a specific flag.
        
        Args:
            flag_name: Name of the flag
            
        Returns:
            Set of file paths
        """
        return {
            u.file_path
            for u in self.usages
            if u.flag_name == flag_name
        }
    
    @property
    def paths(self) -> list[CodePath]:
        """Get the list of analyzed code paths."""
        return self._paths.copy()
    
    @property
    def dependencies(self) -> list[FlagDependency]:
        """Get the list of flag dependencies."""
        return self._dependencies.copy()
    
    @property
    def graph(self) -> nx.DiGraph:
        """Get the dependency graph."""
        return self._graph.copy()
