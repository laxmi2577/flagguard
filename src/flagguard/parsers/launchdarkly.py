"""LaunchDarkly configuration parser."""

import json
from typing import Any

from flagguard.core.models import (
    FlagDefinition,
    FlagType,
    FlagVariation,
    TargetingRule,
)
from flagguard.parsers.base import BaseParser, ParserError


class LaunchDarklyParser(BaseParser):
    """Parser for LaunchDarkly JSON export format.
    
    Handles the standard LaunchDarkly flag export format with
    support for variations, prerequisites, and targeting rules.
    """
    
    def parse(self, content: str) -> list[FlagDefinition]:
        """Parse LaunchDarkly JSON configuration.
        
        Args:
            content: JSON string in LaunchDarkly export format
            
        Returns:
            List of FlagDefinition objects
            
        Raises:
            ParserError: If parsing fails
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ParserError(f"Invalid JSON: {e}") from e
        
        flags_data = data.get("flags", {})
        if not isinstance(flags_data, dict):
            raise ParserError("Expected 'flags' to be an object")
        
        flags: list[FlagDefinition] = []
        
        for flag_key, flag_data in flags_data.items():
            flag = self._parse_flag(flag_key, flag_data)
            flags.append(flag)
        
        return flags
    
    def _parse_flag(self, key: str, data: dict[str, Any]) -> FlagDefinition:
        """Parse a single flag definition."""
        # Get flag name (prefer 'key' if present, fall back to object key)
        name = data.get("key", key)
        
        # Determine flag type from variations
        variations_raw = data.get("variations", [True, False])
        flag_type = self._detect_type(variations_raw)
        
        # Parse variations
        variations = self._parse_variations(variations_raw)
        
        # Parse prerequisites as dependencies
        prerequisites = data.get("prerequisites", [])
        dependencies = [p["key"] for p in prerequisites if "key" in p]
        
        # Parse targeting rules
        rules = data.get("rules", [])
        targeting_rules = self._parse_rules(rules)
        
        # Get enabled state
        enabled = data.get("on", True)
        
        # Get default variation
        fallthrough = data.get("fallthrough", {})
        default_idx = fallthrough.get("variation", 0)
        default_variation = (
            variations[default_idx].name
            if default_idx < len(variations)
            else ""
        )
        
        return FlagDefinition(
            name=name,
            flag_type=flag_type,
            enabled=enabled,
            default_variation=default_variation,
            variations=variations,
            targeting_rules=targeting_rules,
            dependencies=dependencies,
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )
    
    def _detect_type(self, variations: list[Any]) -> FlagType:
        """Detect flag type from variations."""
        if not variations:
            return FlagType.BOOLEAN
        
        first = variations[0]
        if isinstance(first, bool):
            return FlagType.BOOLEAN
        elif isinstance(first, str):
            return FlagType.STRING
        elif isinstance(first, (int, float)):
            return FlagType.NUMBER
        else:
            return FlagType.JSON
    
    def _parse_variations(self, variations: list[Any]) -> list[FlagVariation]:
        """Parse variations into FlagVariation objects."""
        result: list[FlagVariation] = []
        
        for i, value in enumerate(variations):
            if isinstance(value, bool):
                name = "on" if value else "off"
            else:
                name = f"variation_{i}"
            
            result.append(FlagVariation(name=name, value=value))
        
        return result
    
    def _parse_rules(self, rules: list[dict[str, Any]]) -> list[TargetingRule]:
        """Parse targeting rules."""
        result: list[TargetingRule] = []
        
        for i, rule in enumerate(rules):
            conditions = rule.get("clauses", [])
            variation_idx = rule.get("variation", 0)
            rollout = rule.get("rollout", {})
            percentage = rollout.get("variations", [{}])[0].get("weight", 100000) / 1000
            
            result.append(TargetingRule(
                name=rule.get("id", f"rule_{i}"),
                conditions=conditions,
                variation=f"variation_{variation_idx}",
                rollout_percentage=percentage,
            ))
        
        return result
