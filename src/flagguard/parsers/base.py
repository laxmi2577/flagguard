"""Base parser class for feature flag configurations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from flagguard.core.models import FlagDefinition


class ParserError(Exception):
    """Exception raised when parsing fails."""
    pass


class BaseParser(ABC):
    """Abstract base class for flag configuration parsers.
    
    All platform-specific parsers should inherit from this class
    and implement the parse method.
    """
    
    @abstractmethod
    def parse(self, content: str) -> list[FlagDefinition]:
        """Parse configuration content and return flag definitions.
        
        Args:
            content: Raw configuration content (JSON/YAML string)
            
        Returns:
            List of FlagDefinition objects
            
        Raises:
            ParserError: If parsing fails
        """
        pass
    
    def parse_file(self, path: Path) -> list[FlagDefinition]:
        """Parse a configuration file.
        
        Args:
            path: Path to the configuration file
            
        Returns:
            List of FlagDefinition objects
        """
        content = path.read_text(encoding="utf-8")
        return self.parse(content)
    
    @staticmethod
    def detect_format(content: str) -> str:
        """Detect the configuration format from content.
        
        Args:
            content: Raw configuration content
            
        Returns:
            Format identifier: "launchdarkly", "unleash", or "generic"
        """
        content_stripped = content.strip()
        
        # Check for YAML indicators
        if content_stripped.startswith("---") or "features:" in content_stripped[:100]:
            return "unleash"
        
        # Check for LaunchDarkly format
        if '"flags":' in content_stripped and '"variations":' in content_stripped:
            return "launchdarkly"
        
        # Default to generic JSON
        return "generic"
