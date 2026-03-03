"""Markdown report generator."""

from datetime import datetime
from pathlib import Path

from flagguard.core.models import Conflict, ConflictType, DeadCodeBlock, FlagDefinition


class MarkdownReporter:
    """Generates Markdown reports from analysis results.
    
    Creates human-readable reports with sections for:
    - Executive summary
    - Conflicts
    - Dead code
    - Dependency graph
    """
    
    def __init__(self) -> None:
        """Initialize the reporter."""
        self._sections: list[str] = []
    
    def generate_report(
        self,
        flags: list[FlagDefinition],
        conflicts: list[Conflict],
        dead_blocks: list[DeadCodeBlock],
        executive_summary: str = "",
        dependency_graph: str = "",
    ) -> str:
        """Generate a complete Markdown report.
        
        Args:
            flags: List of analyzed flags
            conflicts: Detected conflicts
            dead_blocks: Dead code blocks
            executive_summary: Optional executive summary text
            dependency_graph: Optional Mermaid diagram
            
        Returns:
            Complete Markdown report
        """
        self._sections.clear()
        
        # Split conflicts by type
        mutual_exclusions = [c for c in conflicts if c.conflict_type == ConflictType.MUTUAL_EXCLUSION]
        dependency_violations = [c for c in conflicts if c.conflict_type == ConflictType.DEPENDENCY_VIOLATION]
        
        # Header
        self._add_header(len(flags), len(mutual_exclusions), len(dependency_violations), len(dead_blocks))
        
        # Executive summary
        if executive_summary:
            self._add_section("Executive Summary", executive_summary)
        
        # Conflicts (Mutual Exclusions)
        self._add_conflicts_section(mutual_exclusions)
        
        # Dependency Violations
        self._add_dependency_violations_section(dependency_violations)
        
        # Dead code
        self._add_dead_code_section(dead_blocks)
        
        # Dependency graph
        if dependency_graph:
            self._add_section(
                "Dependency Graph",
                f"```mermaid\n{dependency_graph}\n```"
            )
        
        # FLAG list
        self._add_flags_section(flags)
        
        return "\n\n".join(self._sections)
    
    def _add_header(
        self,
        flag_count: int,
        conflict_count: int,
        dependency_count: int,
        dead_count: int,
    ) -> None:
        """Add report header."""
        total_issues = conflict_count + dependency_count + dead_count
        status = "✅ Healthy" if total_issues == 0 else "⚠️ Issues Found"
        
        header = f"""# FlagGuard Analysis Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Status:** {status}

| Metric | Count |
|--------|-------|
| Flags Analyzed | {flag_count} |
| Mutual Conflicts | {conflict_count} |
| Dependency Errors | {dependency_count} |
| Dead Code Blocks | {dead_count} |"""
        
        self._sections.append(header)
    
    def _add_section(self, title: str, content: str) -> None:
        """Add a section to the report."""
        self._sections.append(f"## {title}\n\n{content}")
    
    def _add_conflicts_section(self, conflicts: list[Conflict]) -> None:
        """Add mutual exclusion conflicts section."""
        if not conflicts:
            self._add_section("Mutual Exclusions", "✅ No mutual exclusion conflicts detected.")
            return
        
        content_parts = []
        
        for conflict in conflicts:
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(conflict.severity.value, "⚪")
            
            flags_str = ", ".join(f"`{f}`" for f in conflict.flags_involved)
            values_str = ", ".join(
                f"`{k}`={v}" for k, v in conflict.conflicting_values.items()
            )
            
            part = f"""### {severity_icon} {conflict.conflict_id}: {flags_str}

**Severity:** {conflict.severity.value.upper()}  
**Conflicting State:** {values_str}

**Reason:** {conflict.reason}
"""
            if conflict.llm_explanation:
                part += f"\n**Explanation:** {conflict.llm_explanation}\n"
            
            if conflict.affected_code_locations:
                locations = ", ".join(conflict.affected_code_locations[:5])
                part += f"\n**Affected Locations:** {locations}\n"
            
            content_parts.append(part)
        
        self._add_section("Mutual Exclusions", "\n---\n".join(content_parts))

    def _add_dependency_violations_section(self, violations: list[Conflict]) -> None:
        """Add dependency violations section."""
        if not violations:
            self._add_section("Dependency Violations", "✅ No dependency violations detected.")
            return

        content_parts = []

        for violation in violations:
            flags_str = " → ".join(f"`{f}`" for f in violation.flags_involved)
            
            part = f"""### ⚠️ {violation.conflict_id}: {flags_str}

**Type:** Dependency Violation  
**Reason:** {violation.reason}
"""
            if violation.llm_explanation:
                part += f"\n**Explanation:** {violation.llm_explanation}\n"
            
            content_parts.append(part)
        
        self._add_section("Dependency Violations", "\n---\n".join(content_parts))
    
    def _add_dead_code_section(self, dead_blocks: list[DeadCodeBlock]) -> None:
        """Add dead code section."""
        if not dead_blocks:
            self._add_section("Dead Code", "No dead code detected.")
            return
        
        total_lines = sum(b.estimated_lines for b in dead_blocks)
        
        content_parts = [f"**Total estimated dead lines:** {total_lines}\n"]
        
        for block in dead_blocks:
            flags_str = ", ".join(
                f"`{k}`={v}" for k, v in block.required_flags.items()
            )
            
            part = f"""### {block.file_path}:{block.start_line}-{block.end_line}

**Required Flags:** {flags_str}  
**Estimated Lines:** {block.estimated_lines}

**Reason:** {block.reason}
"""
            if block.code_snippet:
                part += f"\n```\n{block.code_snippet[:200]}\n```\n"
            
            content_parts.append(part)
        
        self._add_section("Dead Code", "\n---\n".join(content_parts))
    
    def _add_flags_section(self, flags: list[FlagDefinition]) -> None:
        """Add flags inventory section."""
        if not flags:
            return
        
        rows = []
        for flag in flags:
            status = "✅" if flag.enabled else "❌"
            deps = ", ".join(flag.dependencies) if flag.dependencies else "-"
            rows.append(f"| `{flag.name}` | {status} | {flag.flag_type.value} | {deps} |")
        
        content = """| Flag | Enabled | Type | Dependencies |
|------|---------|------|--------------|
""" + "\n".join(rows)
        
        self._add_section("Flags Inventory", content)
    
    def save(self, content: str, path: Path) -> None:
        """Save report to file.
        
        Args:
            content: Report content
            path: Output file path
        """
        path.write_text(content, encoding="utf-8")
