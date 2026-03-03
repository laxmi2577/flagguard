"""Integration tests for CLI with RAG."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from flagguard.cli.main import cli
from flagguard.rag.engine import ChatEngine


@pytest.fixture
def runner():
    """Return a click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_chroma_db(tmp_path):
    """Create a temporary directory for ChromaDB."""
    db_path = tmp_path / "chroma_db"
    return str(db_path)


@patch("flagguard.rag.engine.ChatEngine")
def test_explain_flag_command(mock_engine_cls, runner, sample_launchdarkly_config, mock_chroma_db):
    """Test the explain-flag command."""
    # Setup mock engine
    mock_engine = MagicMock()
    mock_engine.chat.return_value = "This flag is used to control the new checkout flow."
    mock_engine_cls.return_value = mock_engine
    
    # Run command
    result = runner.invoke(cli, [
        "explain-flag",
        "new_checkout",
        "--config", str(sample_launchdarkly_config),
        "--raw"
    ])
    
    # Verify
    assert result.exit_code == 0
    assert "This flag is used to control the new checkout flow." in result.output
    
    # Verify engine called correctly
    mock_engine.chat.assert_called_with("Explain the feature flag 'new_checkout'. Where is it defined and used? What happens if it is enabled/disabled?")


@patch("flagguard.rag.engine.ChatEngine")
def test_explain_flag_missing_db(mock_engine_cls, runner, sample_launchdarkly_config):
    """Test explain-flag when vector store is missing (simulated by checking path)."""
    # Note: The CLI implementation checks path existence before creating engine.
    # We need to ensure the path doesn't exist.
    
    # We can patch Path.exists but that's risky.
    # Instead, let's look at how the CLI determines the path.
    # It seems to default to .flagguard/vector_store in current dir.
    
    with runner.isolated_filesystem():
        # Empty directory, so .flagguard/vector_store definitely doesn't exist
        
        # Create config file here so we can pass it
        config_path = Path("config.json")
        config_path.write_text(sample_launchdarkly_config.read_text())
        
        result = runner.invoke(cli, [
            "explain-flag",
            "new_checkout",
            "--config", str(config_path),
            "--raw"
        ])
        
        # Should fail or return error message about missing DB
        # The CLI currently prints "Vector store not found..."
        assert "Vector store not found" in result.output
        assert result.exit_code == 0  # It returns 0 but prints error
