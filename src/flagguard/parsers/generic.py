"""Generic JSON configuration parser."""

import json
from typing import Any

from flagguard.core.models import (
    FlagDefinition,
    FlagType,
    FlagVariation,
)
from flagguard.parsers.base import BaseParser, ParserError


class GenericParser(BaseParser):
    """Parser for generic JSON configuration format.
    
    Handles a simple, universal JSON format for feature flags:
    {
        "flags": [
            {
                "name": "feature_name",
                "enabled": true,
                "type": "boolean",
                "dependencies": ["other_flag"]
            }
        ]
    }
    """
    
    def parse(self, content: str) -> list[FlagDefinition]:
        """Parse generic JSON configuration.
        
        Args:
            content: JSON string in generic format
            
        Returns:
            List of FlagDefinition objects
            
        Raises:
            ParserError: If parsing fails
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ParserError(f"Invalid JSON: {e}") from e
        
        # Handle both array and object formats
        if isinstance(data, list):
            flags_data = data
        elif isinstance(data, dict):
            flags_data = data.get("flags", [])
            # Also support object-style flags (like LaunchDarkly)
            if isinstance(flags_data, dict):
                flags_data = [
                    {**v, "name": k} for k, v in flags_data.items()
                ]
        else:
            raise ParserError("Expected JSON object or array")
        
        flags: list[FlagDefinition] = []
        
        for flag_data in flags_data:
            flag = self._parse_flag(flag_data)
            flags.append(flag)
        
        return flags
    
    def _parse_flag(self, data: dict[str, Any]) -> FlagDefinition:
        """Parse a single flag definition."""
        name = data.get("name", data.get("key", ""))
        if not name:
            raise ParserError("Flag missing required 'name' field")
        
        # Determine flag type
        type_str = data.get("type", "boolean").lower()
        type_map = {
            "boolean": FlagType.BOOLEAN,
            "bool": FlagType.BOOLEAN,
            "string": FlagType.STRING,
            "str": FlagType.STRING,
            "number": FlagType.NUMBER,
            "int": FlagType.NUMBER,
            "float": FlagType.NUMBER,
            "json": FlagType.JSON,
            "object": FlagType.JSON,
        }
        flag_type = type_map.get(type_str, FlagType.BOOLEAN)
        
        # Get enabled state
        enabled = data.get("enabled", data.get("on", True))
        
        # Parse variations if present
        variations_data = data.get("variations", [])
        if variations_data:
            variations = [
                FlagVariation(
                    name=v.get("name", f"var_{i}") if isinstance(v, dict) else str(v),
                    value=v.get("value", v) if isinstance(v, dict) else v,
                )
                for i, v in enumerate(variations_data)
            ]
        else:
            # Default boolean variations
            variations = [
                FlagVariation(name="on", value=True),
                FlagVariation(name="off", value=False),
            ]
        
        # Get dependencies
        dependencies = data.get("dependencies", data.get("requires", []))
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        
        return FlagDefinition(
            name=name,
            flag_type=flag_type,
            enabled=enabled,
            default_variation=data.get("default", variations[0].name if variations else ""),
            variations=variations,
            targeting_rules=[],
            dependencies=dependencies,
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )
