"""Unit tests for configuration parsers (LaunchDarkly, Generic, Unleash, Factory)."""

import json
from pathlib import Path

import pytest

from flagguard.core.models import FlagType
from flagguard.parsers.base import BaseParser, ParserError
from flagguard.parsers.launchdarkly import LaunchDarklyParser
from flagguard.parsers.generic import GenericParser
from flagguard.parsers.unleash import UnleashParser
from flagguard.parsers.factory import parse_config, get_parser


# ─────────────────────────────────────────────────────────────────
# LaunchDarkly Parser Tests
# ─────────────────────────────────────────────────────────────────

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

    def test_parse_empty_flags_dict(self) -> None:
        """Empty flags object should return empty list."""
        parser = LaunchDarklyParser()
        config = json.dumps({"flags": {}})

        flags = parser.parse(config)

        assert flags == []

    def test_parse_multiple_prerequisites(self) -> None:
        """Flag with multiple prerequisites => multiple dependencies."""
        parser = LaunchDarklyParser()
        config = json.dumps({
            "flags": {
                "advanced_feature": {
                    "on": True,
                    "variations": [True, False],
                    "prerequisites": [
                        {"key": "base_feature"},
                        {"key": "auth_enabled"},
                    ],
                }
            }
        })

        flags = parser.parse(config)

        assert "base_feature" in flags[0].dependencies
        assert "auth_enabled" in flags[0].dependencies

    def test_parse_disabled_flag(self) -> None:
        """Disabled flag should have enabled=False."""
        parser = LaunchDarklyParser()
        config = json.dumps({
            "flags": {
                "deprecated": {
                    "on": False,
                    "variations": [True, False],
                }
            }
        })

        flags = parser.parse(config)

        assert flags[0].enabled is False

    def test_parse_numeric_variations(self) -> None:
        """Integer/numeric variations should be handled."""
        parser = LaunchDarklyParser()
        config = json.dumps({
            "flags": {
                "rate_limit": {
                    "on": True,
                    "variations": [10, 50, 100],
                }
            }
        })

        flags = parser.parse(config)

        assert flags[0].flag_type == FlagType.NUMBER
        assert len(flags[0].variations) == 3

    def test_parse_multiple_flags(self) -> None:
        """Should parse all flags from a multi-flag config."""
        parser = LaunchDarklyParser()
        config = json.dumps({
            "flags": {
                "flag_a": {"on": True, "variations": [True, False]},
                "flag_b": {"on": False, "variations": [True, False]},
                "flag_c": {"on": True, "variations": ["a", "b"]},
            }
        })

        flags = parser.parse(config)

        assert len(flags) == 3
        names = {f.name for f in flags}
        assert names == {"flag_a", "flag_b", "flag_c"}

    def test_parse_flag_with_description_and_tags(self) -> None:
        """Description and tags should be captured."""
        parser = LaunchDarklyParser()
        config = json.dumps({
            "flags": {
                "tagged_flag": {
                    "on": True,
                    "variations": [True, False],
                    "description": "A test flag with tags",
                    "tags": ["ui", "checkout"],
                }
            }
        })

        flags = parser.parse(config)

        assert flags[0].description == "A test flag with tags"
        assert "ui" in flags[0].tags
        assert "checkout" in flags[0].tags

    def test_parse_file_method(self, sample_launchdarkly_config: Path) -> None:
        """Test parse_file convenience method."""
        parser = LaunchDarklyParser()
        flags = parser.parse_file(sample_launchdarkly_config)

        assert len(flags) > 0


# ─────────────────────────────────────────────────────────────────
# Generic Parser Tests
# ─────────────────────────────────────────────────────────────────

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

    def test_parse_empty_array(self) -> None:
        """Empty array config should return empty list."""
        parser = GenericParser()
        flags = parser.parse("[]")

        assert flags == []

    def test_parse_empty_flags_object(self) -> None:
        """Object with empty flags array returns empty."""
        parser = GenericParser()
        config = json.dumps({"flags": []})

        flags = parser.parse(config)

        assert flags == []

    def test_parse_invalid_json_raises(self) -> None:
        """Invalid JSON should raise ParserError."""
        parser = GenericParser()

        with pytest.raises(ParserError):
            parser.parse("not valid json")

    def test_parse_flag_with_all_fields(self) -> None:
        """Flag with type, description, and dependencies."""
        parser = GenericParser()
        config = json.dumps([
            {
                "name": "feature_x",
                "enabled": True,
                "type": "string",
                "dependencies": ["feature_y"],
                "description": "Test feature",
            },
        ])

        flags = parser.parse(config)

        assert flags[0].name == "feature_x"
        assert "feature_y" in flags[0].dependencies

    def test_parse_multiple_dependencies(self) -> None:
        """Flag with multiple dependencies."""
        parser = GenericParser()
        config = json.dumps({
            "flags": [
                {"name": "base_a", "enabled": True},
                {"name": "base_b", "enabled": True},
                {"name": "child", "enabled": True, "dependencies": ["base_a", "base_b"]},
            ]
        })

        flags = parser.parse(config)
        child = next(f for f in flags if f.name == "child")

        assert len(child.dependencies) == 2


# ─────────────────────────────────────────────────────────────────
# Unleash Parser Tests (NEW)
# ─────────────────────────────────────────────────────────────────

class TestUnleashParser:
    """Tests for Unleash YAML/JSON parser."""

    def test_parse_basic_yaml_feature(self) -> None:
        """Parse basic Unleash YAML with a single enabled feature."""
        parser = UnleashParser()
        content = """
features:
  - name: my-feature
    enabled: true
"""
        flags = parser.parse(content)

        assert len(flags) == 1
        assert flags[0].name == "my-feature"
        assert flags[0].enabled is True
        assert flags[0].flag_type == FlagType.BOOLEAN

    def test_parse_disabled_feature(self) -> None:
        """Disabled features should have enabled=False."""
        parser = UnleashParser()
        content = """
features:
  - name: old-feature
    enabled: false
"""
        flags = parser.parse(content)

        assert flags[0].enabled is False

    def test_parse_multiple_features(self) -> None:
        """Parse config with multiple features."""
        parser = UnleashParser()
        content = """
features:
  - name: feature-alpha
    enabled: true
  - name: feature-beta
    enabled: false
  - name: feature-gamma
    enabled: true
"""
        flags = parser.parse(content)

        assert len(flags) == 3
        names = {f.name for f in flags}
        assert names == {"feature-alpha", "feature-beta", "feature-gamma"}

    def test_parse_with_variants(self) -> None:
        """Parse features with variant definitions."""
        parser = UnleashParser()
        content = """
features:
  - name: experiment
    enabled: true
    variants:
      - name: control
        weight: 50
      - name: treatment
        weight: 50
"""
        flags = parser.parse(content)

        assert len(flags[0].variations) == 2
        var_names = {v.name for v in flags[0].variations}
        assert "control" in var_names
        assert "treatment" in var_names

    def test_parse_with_strategies(self) -> None:
        """Parse features with strategy definitions."""
        parser = UnleashParser()
        content = """
features:
  - name: rollout-feature
    enabled: true
    strategies:
      - name: gradualRollout
        parameters:
          percentage: 50
"""
        flags = parser.parse(content)

        assert len(flags[0].targeting_rules) == 1
        rule = flags[0].targeting_rules[0]
        assert rule.rollout_percentage == 50.0

    def test_parse_with_user_strategy(self) -> None:
        """Parse userWithId strategy."""
        parser = UnleashParser()
        content = """
features:
  - name: beta-feature
    enabled: true
    strategies:
      - name: userWithId
        parameters:
          userIds: "user1,user2,user3"
"""
        flags = parser.parse(content)

        assert len(flags[0].targeting_rules) == 1

    def test_parse_empty_features(self) -> None:
        """Empty features list returns empty result."""
        parser = UnleashParser()
        content = """
features: []
"""
        flags = parser.parse(content)
        assert flags == []

    def test_parse_json_format(self) -> None:
        """Unleash parser also handles JSON format."""
        parser = UnleashParser()
        content = json.dumps({
            "features": [
                {"name": "json-feature", "enabled": True}
            ]
        })

        flags = parser.parse(content)

        assert len(flags) == 1
        assert flags[0].name == "json-feature"

    def test_parse_malformed_yaml_raises(self) -> None:
        """Malformed YAML/JSON should raise ParserError."""
        parser = UnleashParser()

        with pytest.raises((ParserError, Exception)):
            parser.parse("{{{{invalid yaml: [[[")

    def test_parse_feature_with_description(self) -> None:
        """Features with description field."""
        parser = UnleashParser()
        content = """
features:
  - name: described-feature
    enabled: true
    description: "A well-documented feature"
"""
        flags = parser.parse(content)
        assert flags[0].description == "A well-documented feature"

    def test_parse_feature_with_tags(self) -> None:
        """Features with tags."""
        parser = UnleashParser()
        content = """
features:
  - name: tagged-feature
    enabled: true
    tags:
      - value: backend
      - value: api
"""
        flags = parser.parse(content)
        assert "backend" in flags[0].tags
        assert "api" in flags[0].tags

    def test_parse_none_content(self) -> None:
        """Null YAML content should return empty list."""
        parser = UnleashParser()
        # YAML parsing of empty string yields None
        flags = parser.parse("")
        assert flags == []

    def test_parse_feature_missing_name_raises(self) -> None:
        """Feature without name field should raise error."""
        parser = UnleashParser()
        content = """
features:
  - enabled: true
"""
        with pytest.raises(ParserError, match="name"):
            parser.parse(content)

    def test_parse_with_constraints(self) -> None:
        """Parse strategies with constraints."""
        parser = UnleashParser()
        content = """
features:
  - name: constrained-feature
    enabled: true
    strategies:
      - name: default
        constraints:
          - contextName: country
            operator: IN
            values:
              - US
              - UK
"""
        flags = parser.parse(content)
        assert len(flags[0].targeting_rules) == 1

    def test_parse_variant_with_payload(self) -> None:
        """Variants with payloads should set correct flag type."""
        parser = UnleashParser()
        content = """
features:
  - name: payload-feature
    enabled: true
    variants:
      - name: variant-a
        weight: 50
        payload:
          type: string
          value: "hello"
      - name: variant-b
        weight: 50
        payload:
          type: string
          value: "world"
"""
        flags = parser.parse(content)
        assert flags[0].flag_type == FlagType.STRING


# ─────────────────────────────────────────────────────────────────
# Parser Factory Tests
# ─────────────────────────────────────────────────────────────────

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

    def test_get_unleash_parser(self) -> None:
        """Test getting Unleash parser."""
        parser = get_parser("unleash")
        assert isinstance(parser, UnleashParser)

    def test_parse_config_auto_detect(self, sample_generic_config: Path) -> None:
        """Test auto-detection of format."""
        flags = parse_config(sample_generic_config)
        assert len(flags) == 3

    def test_parse_config_file_not_found(self, tmp_path: Path) -> None:
        """Test error for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_config(tmp_path / "nonexistent.json")

    def test_parse_config_launchdarkly_format(self, sample_launchdarkly_config: Path) -> None:
        """Auto-detect LaunchDarkly format."""
        flags = parse_config(sample_launchdarkly_config)
        assert len(flags) > 0

    def test_parse_yaml_auto_detect(self, tmp_path: Path) -> None:
        """Auto-detect YAML format as Unleash."""
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text("""
features:
  - name: yaml-feature
    enabled: true
""")
        flags = parse_config(yaml_path)
        assert len(flags) == 1


# ─────────────────────────────────────────────────────────────────
# Format Detection Tests
# ─────────────────────────────────────────────────────────────────

class TestFormatDetection:
    """Tests for BaseParser.detect_format static method."""

    def test_detect_launchdarkly_format(self) -> None:
        """LaunchDarkly format detection."""
        content = json.dumps({
            "flags": {
                "test": {"on": True, "variations": [True, False]}
            }
        })
        assert BaseParser.detect_format(content) == "launchdarkly"

    def test_detect_unleash_yaml_format(self) -> None:
        """YAML with features key detected as Unleash."""
        content = """
features:
  - name: test
    enabled: true
"""
        assert BaseParser.detect_format(content) == "unleash"

    def test_detect_yaml_header_format(self) -> None:
        """YAML with --- header detected as Unleash."""
        content = """---
features:
  - name: test
"""
        assert BaseParser.detect_format(content) == "unleash"

    def test_detect_generic_format(self) -> None:
        """Generic JSON format detection."""
        content = json.dumps([{"name": "flag", "enabled": True}])
        assert BaseParser.detect_format(content) == "generic"
