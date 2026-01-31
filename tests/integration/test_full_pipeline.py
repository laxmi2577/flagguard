"""Integration tests for FlagGuard full analysis pipeline."""

import json
import pytest
from pathlib import Path


class TestFullPipeline:
    """Test complete analysis flow from config to report."""
    
    def test_analyze_clean_config(
        self,
        sample_launchdarkly_config: Path,
        sample_python_source: Path,
        tmp_path: Path,
    ) -> None:
        """Analyze config without critical conflicts."""
        from flagguard.core.orchestrator import FlagGuardAnalyzer
        
        analyzer = FlagGuardAnalyzer(explain_with_llm=False)
        
        output_path = tmp_path / "report.md"
        report = analyzer.analyze(
            config_path=sample_launchdarkly_config,
            source_path=sample_python_source.parent,
            output_path=output_path,
            output_format="markdown",
        )
        
        assert report["flags_analyzed"] > 0
        assert output_path.exists()
        assert "# FlagGuard Analysis Report" in output_path.read_text()
    
    def test_analyze_with_json_output(
        self,
        sample_launchdarkly_config: Path,
        sample_python_source: Path,
        tmp_path: Path,
    ) -> None:
        """Test JSON report output format."""
        from flagguard.core.orchestrator import FlagGuardAnalyzer
        
        analyzer = FlagGuardAnalyzer(explain_with_llm=False)
        
        output_path = tmp_path / "report.json"
        report = analyzer.analyze(
            config_path=sample_launchdarkly_config,
            source_path=sample_python_source.parent,
            output_path=output_path,
            output_format="json",
        )
        
        assert output_path.exists()
        
        # Verify it's valid JSON
        data = json.loads(output_path.read_text())
        assert "timestamp" in data
        assert "conflicts" in data
    
    def test_analyze_flags_with_dependencies(
        self,
        tmp_path: Path,
    ) -> None:
        """Test analysis with flag dependencies."""
        from flagguard.core.orchestrator import FlagGuardAnalyzer
        
        # Create config with dependency chain
        config = {
            "flags": {
                "parent": {"on": True, "variations": [True, False]},
                "child": {
                    "on": True,
                    "variations": [True, False],
                    "prerequisites": [{"key": "parent"}],
                },
            }
        }
        
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))
        
        # Create minimal source
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        (source_dir / "app.py").write_text('if is_enabled("child"): pass')
        
        analyzer = FlagGuardAnalyzer(explain_with_llm=False)
        report = analyzer.analyze(
            config_path=config_path,
            source_path=source_dir,
        )
        
        assert report["flags_analyzed"] == 2
        assert report["files_scanned"] == 1


class TestCLIIntegration:
    """Test CLI commands end-to-end."""
    
    def test_cli_analyze_command(
        self,
        sample_launchdarkly_config: Path,
        sample_python_source: Path,
    ) -> None:
        """Test CLI analyze command."""
        from click.testing import CliRunner
        from flagguard.cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "analyze",
            "--config", str(sample_launchdarkly_config),
            "--source", str(sample_python_source.parent),
            "--no-llm",
            "--format", "text",
        ])
        
        # May exit 1 if conflicts found, check output
        assert "Loaded" in result.output or "flags" in result.output.lower()
    
    def test_cli_parse_command(
        self,
        sample_launchdarkly_config: Path,
    ) -> None:
        """Test CLI parse command."""
        from click.testing import CliRunner
        from flagguard.cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "parse",
            "--config", str(sample_launchdarkly_config),
        ])
        
        assert result.exit_code == 0
        # Should show table with flag names
        assert "new_checkout" in result.output or "Name" in result.output
    
    def test_cli_graph_command(
        self,
        sample_launchdarkly_config: Path,
        tmp_path: Path,
    ) -> None:
        """Test CLI graph command."""
        from click.testing import CliRunner
        from flagguard.cli.main import cli
        
        runner = CliRunner()
        output_file = tmp_path / "graph.mmd"
        
        result = runner.invoke(cli, [
            "graph",
            "--config", str(sample_launchdarkly_config),
            "--output", str(output_file),
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        assert "flowchart" in output_file.read_text()
    
    def test_cli_init_command(
        self,
        tmp_path: Path,
    ) -> None:
        """Test CLI init command."""
        from click.testing import CliRunner
        from flagguard.cli.main import cli
        import os
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
            
            assert result.exit_code == 0
            assert (tmp_path / ".flagguard.yaml").exists()
        finally:
            os.chdir(original_cwd)
