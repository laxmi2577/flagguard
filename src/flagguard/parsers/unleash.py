"""Unleash configuration parser."""

import json
from typing import Any

import yaml

from flagguard.core.models import (
    FlagDefinition,
    FlagType,
    FlagVariation,
    TargetingRule,
)
from flagguard.parsers.base import BaseParser, ParserError


class UnleashParser(BaseParser):
    """Parser for Unleash YAML/JSON configuration format.
    
    Handles both YAML and JSON formats used by Unleash feature toggles,
    including support for strategies and variants.
    """
    
    def parse(self, content: str) -> list[FlagDefinition]:
        """Parse Unleash configuration.
        
        Args:
            content: YAML or JSON string in Unleash format
            
        Returns:
            List of FlagDefinition objects
            
        Raises:
            ParserError: If parsing fails
        """
        # Try YAML first (also handles JSON as valid YAML)
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            # Fall back to JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                raise ParserError(f"Failed to parse as YAML or JSON: {e}") from e
        
        if data is None:
            return []
        
        features = data.get("features", [])
        if not isinstance(features, list):
            raise ParserError("Expected 'features' to be an array")
        
        flags: list[FlagDefinition] = []
        
        for feature in features:
            flag = self._parse_feature(feature)
            flags.append(flag)
        
        return flags
    
    def _parse_feature(self, data: dict[str, Any]) -> FlagDefinition:
        """Parse a single feature toggle definition."""
        name = data.get("name", "")
        if not name:
            raise ParserError("Feature missing required 'name' field")
        
        enabled = data.get("enabled", True)
        
        # Parse variants as variations
        variants = data.get("variants", [])
        variations = self._parse_variants(variants)
        
        # If no variants, create default boolean variations
        if not variations:
            variations = [
                FlagVariation(name="on", value=True),
                FlagVariation(name="off", value=False),
            ]
        
        # Determine flag type
        flag_type = FlagType.BOOLEAN
        if variants:
            first_variant = variants[0]
            payload = first_variant.get("payload", {})
            if payload.get("type") == "string":
                flag_type = FlagType.STRING
            elif payload.get("type") == "number":
                flag_type = FlagType.NUMBER
            elif payload.get("type") == "json":
                flag_type = FlagType.JSON
        
        # Parse strategies as targeting rules
        strategies = data.get("strategies", [])
        targeting_rules = self._parse_strategies(strategies)
        
        return FlagDefinition(
            name=name,
            flag_type=flag_type,
            enabled=enabled,
            default_variation=variations[0].name if variations else "",
            variations=variations,
            targeting_rules=targeting_rules,
            dependencies=[],  # Unleash doesn't have native dependencies
            description=data.get("description", ""),
            tags=[t.get("value", t) if isinstance(t, dict) else str(t) 
                  for t in data.get("tags", [])],
        )
    
    def _parse_variants(self, variants: list[dict[str, Any]]) -> list[FlagVariation]:
        """Parse Unleash variants into variations."""
        result: list[FlagVariation] = []
        
        for variant in variants:
            name = variant.get("name", "")
            payload = variant.get("payload", {})
            value = payload.get("value", name)
            
            result.append(FlagVariation(
                name=name,
                value=value,
                description="",
            ))
        
        return result
    
    def _parse_strategies(
        self,
        strategies: list[dict[str, Any]],
    ) -> list[TargetingRule]:
        """Parse Unleash strategies into targeting rules."""
        result: list[TargetingRule] = []
        
        for i, strategy in enumerate(strategies):
            name = strategy.get("name", f"strategy_{i}")
            parameters = strategy.get("parameters", {})
            constraints = strategy.get("constraints", [])
            
            # Convert parameters to conditions
            conditions: list[dict[str, Any]] = []
            
            # Handle common strategies
            if name == "userWithId":
                user_ids = parameters.get("userIds", "")
                if user_ids:
                    conditions.append({
                        "attribute": "userId",
                        "op": "in",
                        "values": user_ids.split(","),
                    })
            elif name == "gradualRollout":
                percentage = int(parameters.get("percentage", 100))
                conditions.append({
                    "attribute": "rollout",
                    "op": "percentage",
                    "values": [percentage],
                })
            
            # Add constraints
            for constraint in constraints:
                conditions.append({
                    "attribute": constraint.get("contextName", ""),
                    "op": constraint.get("operator", "IN"),
                    "values": constraint.get("values", []),
                })
            
            result.append(TargetingRule(
                name=f"{name}_{i}",
                conditions=conditions,
                variation="on",
                rollout_percentage=float(parameters.get("percentage", 100)),
            ))
        
        return result
