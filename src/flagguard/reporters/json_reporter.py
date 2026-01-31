"""JSON report generator for CI/CD integration."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from flagguard.core.models import Conflict, DeadCodeBlock, FlagDefinition


class JSONReporter:
    """Generates JSON reports from analysis results.
    
    Creates machine-readable reports suitable for CI/CD pipelines,
    with structured data for automated processing.
    """
    
    def generate_report(
        self,
        flags: list[FlagDefinition],
        conflicts: list[Conflict],
        dead_blocks: list[DeadCodeBlock],
        executive_summary: str = "",
    ) -> dict[str, Any]:
        """Generate a JSON-serializable report.
        
        Args:
            flags: List of analyzed flags
            conflicts: Detected conflicts
            dead_blocks: Dead code blocks
            executive_summary: Optional summary text
            
        Returns:
            Dictionary containing the analysis report
        """
        return {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_flags": len(flags),
                "total_conflicts": len(conflicts),
                "total_dead_code_blocks": len(dead_blocks),
                "total_dead_lines": sum(b.estimated_lines for b in dead_blocks),
                "status": "pass" if len(conflicts) == 0 else "fail",
                "executive_summary": executive_summary,
            },
            "flags": [f.to_dict() for f in flags],
            "conflicts": [c.to_dict() for c in conflicts],
            "dead_code": [d.to_dict() for d in dead_blocks],
            "statistics": self._generate_statistics(flags, conflicts, dead_blocks),
        }
    
    def _generate_statistics(
        self,
        flags: list[FlagDefinition],
        conflicts: list[Conflict],
        dead_blocks: list[DeadCodeBlock],
    ) -> dict[str, Any]:
        """Generate analysis statistics."""
        # Conflict severity breakdown
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for c in conflicts:
            severity_counts[c.severity.value] += 1
        
        # Flag type breakdown
        type_counts: dict[str, int] = {}
        for f in flags:
            type_counts[f.flag_type.value] = type_counts.get(f.flag_type.value, 0) + 1
        
        # Enabled/disabled counts
        enabled_count = sum(1 for f in flags if f.enabled)
        
        return {
            "conflict_severity": severity_counts,
            "flag_types": type_counts,
            "enabled_flags": enabled_count,
            "disabled_flags": len(flags) - enabled_count,
            "flags_with_dependencies": sum(1 for f in flags if f.dependencies),
            "dead_code_files": len(set(b.file_path for b in dead_blocks)),
        }
    
    def save(self, report: dict[str, Any], path: Path) -> None:
        """Save report to JSON file.
        
        Args:
            report: Report dictionary
            path: Output file path
        """
        path.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )
    
    def to_string(self, report: dict[str, Any], pretty: bool = True) -> str:
        """Convert report to JSON string.
        
        Args:
            report: Report dictionary
            pretty: Whether to format with indentation
            
        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(report, indent=2, default=str)
        return json.dumps(report, default=str)
