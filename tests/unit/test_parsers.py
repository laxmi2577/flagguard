"""Unit tests for configuration parsers."""

import json
from pathlib import Path

import pytest

from flagguard.core.models import FlagType
from flagguard.parsers.base import ParserError
from flagguard.parsers.launchdarkly import LaunchDarklyParser
from flagguard.parsers.generic import GenericParser
from flagguard.parsers.factory import parse_config, get_parser


class TestLaunchDarklyParser:
    """Tests for LaunchDarkly parser."""
    
    def test_parse_minimal_flag(self) -> None:
        """Test parsing a minimal flag definition."""
        parser = LaunchDarklyParser()
        config = json.dumps({
            "flags": {
                "test_flag": {
                    "on": True,
                    "variations": [True, False],
                }
            }
        })
        
        flags = parser.parse(config)
        
        assert len(flags) == 1
        assert flags[0].name == "test_flag"
        assert flags[0].enabled is True
        assert flags[0].flag_type == FlagType.BOOLEAN
    
    def test_parse_with_prerequisites(self, sample_launchdarkly_config: Path) -> None:
        """Test parsing flags with prerequisites."""
        parser = LaunchDarklyParser()
        content = sample_launchdarkly_config.read_text()
        
        flags = parser.parse(content)
        
        # Find new_checkout flag
        checkout = next(f for f in flags if f.name == "new_checkout")
        assert "payment_enabled" in checkout.dependencies
    
    def test_parse_invalid_json(self) -> None:
        """Test error handling for invalid JSON."""
        parser = LaunchDarklyParser()
        
        with pytest.raises(ParserError, match="Invalid JSON"):
            parser.parse("not valid json")
    
    def test_parse_string_variations(self) -> None:
        """Test parsing flags with string variations."""
        parser = LaunchDarklyParser()
        config = json.dumps({
            "flags": {
                "ab_test": {
                    "on": True,
                    "variations": ["control", "variant_a", "variant_b"],
                }
            }
        })
        
        flags = parser.parse(config)
        
        assert flags[0].flag_type == FlagType.STRING
        assert len(flags[0].variations) == 3


class TestGenericParser:
    """Tests for generic JSON parser."""
    
    def test_parse_array_format(self) -> None:
        """Test parsing array format."""
        parser = GenericParser()
        config = json.dumps([
            {"name": "flag_a", "enabled": True},
            {"name": "flag_b", "enabled": False},
        ])
        
        flags = parser.parse(config)
        
        assert len(flags) == 2
        assert flags[0].name == "flag_a"
        assert flags[1].name == "flag_b"
    
    def test_parse_object_format(self, sample_generic_config: Path) -> None:
        """Test parsing object format with flags array."""
        parser = GenericParser()
        content = sample_generic_config.read_text()
        
        flags = parser.parse(content)
        
        assert len(flags) == 3
    
    def test_parse_with_dependencies(self) -> None:
        """Test parsing dependencies."""
        parser = GenericParser()
        config = json.dumps({
            "flags": [
                {"name": "parent", "enabled": True},
                {"name": "child", "enabled": True, "dependencies": ["parent"]},
            ]
        })
        
        flags = parser.parse(config)
        child = next(f for f in flags if f.name == "child")
        
        assert "parent" in child.dependencies


class TestParserFactory:
    """Tests for parser factory."""
    
    def test_get_launchdarkly_parser(self) -> None:
        """Test getting LaunchDarkly parser."""
        parser = get_parser("launchdarkly")
        assert isinstance(parser, LaunchDarklyParser)
    
    def test_get_generic_parser(self) -> None:
        """Test getting generic parser."""
        parser = get_parser("generic")
        assert isinstance(parser, GenericParser)
    
    def test_parse_config_auto_detect(self, sample_generic_config: Path) -> None:
        """Test auto-detection of format."""
        flags = parse_config(sample_generic_config)
        assert len(flags) == 3
    
    def test_parse_config_file_not_found(self, tmp_path: Path) -> None:
        """Test error for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_config(tmp_path / "nonexistent.json")
