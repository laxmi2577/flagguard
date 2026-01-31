"""Main orchestrator for FlagGuard analysis.

Coordinates the entire analysis pipeline from parsing
through conflict detection to report generation.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from flagguard.core.models import FlagDefinition
from flagguard.core.logging import get_logger

logger = get_logger("orchestrator")


class FlagGuardAnalyzer:
    """Main entry point for FlagGuard analysis.
    
    Orchestrates the full analysis pipeline:
    1. Parse configuration files
    2. Scan source code for flag usages
    3. Encode constraints for SAT solving
    4. Detect conflicts and dead code
    5. Generate explanations with LLM
    6. Create reports
    
    Attributes:
        explain_with_llm: Whether to use LLM for explanations
        output_format: Default output format ("markdown" or "json")
    """
    
    def __init__(
        self,
        explain_with_llm: bool = True,
        output_format: str = "markdown",
    ) -> None:
        """Initialize the analyzer.
        
        Args:
            explain_with_llm: Whether to generate LLM explanations
            output_format: Default report format
        """
        self.explain_with_llm = explain_with_llm
        self.output_format = output_format
    
    def analyze(
        self,
        config_path: Path,
        source_path: Path,
        output_path: Path | None = None,
        output_format: str | None = None,
    ) -> dict[str, Any]:
        """Run the full analysis pipeline.
        
        Args:
            config_path: Path to flag configuration file
            source_path: Path to source code directory
            output_path: Optional path to save report
            output_format: Override default output format
            
        Returns:
            Dictionary containing analysis results
        """
        format_to_use = output_format or self.output_format
        
        logger.info(f"Starting analysis: config={config_path}, source={source_path}")
        
        # Step 1: Parse configuration
        logger.info("Step 1: Parsing flag configuration...")
        flags = self._parse_config(config_path)
        logger.info(f"  Loaded {len(flags)} flags")
        
        # Step 2: Scan source code
        logger.info("Step 2: Scanning source code for flag usages...")
        usages_db = self._scan_source(source_path)
        logger.info(f"  Scanned {usages_db.files_scanned} files, found {len(usages_db.usages)} usages")
        
        # Step 3: Build constraints and detect conflicts
        logger.info("Step 3: Detecting conflicts...")
        conflicts = self._detect_conflicts(flags, usages_db.usages)
        logger.info(f"  Found {len(conflicts)} conflicts")
        
        # Step 4: Find dead code
        logger.info("Step 4: Finding dead code...")
        dead_code = self._find_dead_code(flags, usages_db.usages)
        logger.info(f"  Found {len(dead_code)} dead code blocks")
        
        # Step 5: Build dependency graph
        logger.info("Step 5: Building dependency graph...")
        dep_graph = self._build_dependency_graph(flags, usages_db.usages)
        
        # Step 6: Generate explanations
        explanations = []
        executive_summary = ""
        if self.explain_with_llm:
            logger.info("Step 6: Generating LLM explanations...")
            explanations, executive_summary = self._generate_explanations(
                flags, conflicts, dead_code, usages_db.files_scanned
            )
        
        # Step 7: Create report
        report = {
            "timestamp": datetime.now().isoformat(),
            "config_file": str(config_path),
            "source_path": str(source_path),
            "flags_analyzed": len(flags),
            "files_scanned": usages_db.files_scanned,
            "conflicts": conflicts,
            "dead_code": dead_code,
            "dependency_graph": dep_graph,
            "explanations": explanations,
            "executive_summary": executive_summary,
        }
        
        # Step 8: Save report if output path provided
        if output_path:
            logger.info(f"Step 8: Saving report to {output_path}...")
            self._save_report(report, output_path, format_to_use)
        
        logger.info("Analysis complete!")
        return report
    
    def _parse_config(self, config_path: Path) -> list[FlagDefinition]:
        """Parse flag configuration file."""
        from flagguard.parsers import parse_config
        return parse_config(config_path)
    
    def _scan_source(self, source_path: Path) -> Any:
        """Scan source code for flag usages."""
        from flagguard.parsers.ast import SourceScanner
        scanner = SourceScanner()
        return scanner.scan_directory(source_path)
    
    def _detect_conflicts(
        self,
        flags: list[FlagDefinition],
        usages: list,
    ) -> list[dict]:
        """Detect flag conflicts."""
        from flagguard.analysis import ConstraintEncoder, ConflictDetector
        
        encoder = ConstraintEncoder()
        solver = encoder.encode_flags(flags)
        encoder.encode_usage_constraints(usages, flags)
        
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        return [
            {
                "id": c.conflict_id,
                "flags": c.flags_involved,
                "values": c.conflicting_values,
                "severity": c.severity.value,
                "reason": c.reason,
            }
            for c in conflicts
        ]
    
    def _find_dead_code(
        self,
        flags: list[FlagDefinition],
        usages: list,
    ) -> list[dict]:
        """Find dead code blocks."""
        from flagguard.analysis import ConstraintEncoder, DeadCodeFinder
        
        encoder = ConstraintEncoder()
        solver = encoder.encode_flags(flags)
        
        finder = DeadCodeFinder(solver)
        blocks = finder.find_dead_code(usages)
        
        return [
            {
                "file": b.file_path,
                "start_line": b.start_line,
                "end_line": b.end_line,
                "required_flags": b.required_flags,
                "reason": b.reason,
            }
            for b in blocks
        ]
    
    def _build_dependency_graph(
        self,
        flags: list[FlagDefinition],
        usages: list,
    ) -> dict:
        """Build flag dependency graph."""
        from flagguard.analysis import PathAnalyzer
        
        analyzer = PathAnalyzer()
        graph = analyzer.build_dependency_graph(flags, usages)
        
        return {
            "mermaid": graph.to_mermaid() if hasattr(graph, 'to_mermaid') else "",
            "cycles": graph.detect_cycles() if hasattr(graph, 'detect_cycles') else [],
        }
    
    def _generate_explanations(
        self,
        flags: list[FlagDefinition],
        conflicts: list[dict],
        dead_code: list[dict],
        files_scanned: int,
    ) -> tuple[list[dict], str]:
        """Generate LLM explanations."""
        from flagguard.llm import ConflictExplainer
        
        try:
            explainer = ConflictExplainer()
            
            # Convert dicts back to Conflict objects for explainer
            # For now, return simplified explanations
            explanations = []
            for conflict in conflicts[:10]:
                explanations.append({
                    "id": conflict["id"],
                    "explanation": conflict["reason"],
                })
            
            # Generate executive summary
            critical_count = len([c for c in conflicts if c["severity"] == "critical"])
            executive_summary = explainer.generate_executive_summary(
                total_flags=len(flags),
                conflict_count=len(conflicts),
                critical_count=critical_count,
                dead_code_count=len(dead_code),
                files_scanned=files_scanned,
            )
            
            return explanations, executive_summary
            
        except Exception as e:
            logger.warning(f"LLM explanation failed: {e}")
            return [], f"Analysis summary: {len(conflicts)} conflicts, {len(dead_code)} dead code blocks."
    
    def _save_report(
        self,
        report: dict,
        output_path: Path,
        format: str,
    ) -> None:
        """Save report to file."""
        import json
        
        if format == "json":
            output_path.write_text(
                json.dumps(report, indent=2, default=str),
                encoding="utf-8"
            )
        else:
            # Markdown format
            md_content = self._generate_markdown(report)
            output_path.write_text(md_content, encoding="utf-8")
    
    def _generate_markdown(self, report: dict) -> str:
        """Generate markdown report content."""
        lines = [
            "# FlagGuard Analysis Report",
            "",
            f"**Generated:** {report['timestamp']}",
            f"**Config:** `{report['config_file']}`",
            f"**Source:** `{report['source_path']}`",
            "",
            "---",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Flags Analyzed | {report['flags_analyzed']} |",
            f"| Files Scanned | {report['files_scanned']} |",
            f"| Conflicts Found | {len(report['conflicts'])} |",
            f"| Dead Code Blocks | {len(report['dead_code'])} |",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            report.get('executive_summary', 'No summary available.'),
            "",
            "---",
            "",
        ]
        
        # Conflicts section
        lines.append("## Conflicts")
        lines.append("")
        if not report['conflicts']:
            lines.append("✅ No conflicts detected!")
        else:
            for conflict in report['conflicts']:
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(conflict['severity'], "⚪")
                
                lines.append(f"### {severity_emoji} {conflict['id']}: {', '.join(conflict['flags'])}")
                lines.append(f"**Severity:** {conflict['severity'].title()}")
                lines.append(f"**Reason:** {conflict['reason']}")
                lines.append("")
        
        # Dead code section
        lines.append("")
        lines.append("## Dead Code")
        lines.append("")
        if not report['dead_code']:
            lines.append("✅ No dead code detected!")
        else:
            for block in report['dead_code']:
                lines.append(f"### {block['file']}:{block['start_line']}-{block['end_line']}")
                lines.append(f"**Reason:** {block['reason']}")
                lines.append("")
        
        # Footer
        lines.extend([
            "",
            "---",
            "",
            "*Generated by FlagGuard*",
        ])
        
        return "\n".join(lines)
