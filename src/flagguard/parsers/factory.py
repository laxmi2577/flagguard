"""Parser factory for automatic format detection and parser selection."""

from pathlib import Path
from typing import Literal

from flagguard.core.models import FlagDefinition
from flagguard.parsers.base import BaseParser, ParserError


ParserType = Literal["launchdarkly", "unleash", "generic", "auto"]


def get_parser(parser_type: ParserType = "auto") -> BaseParser:
    """Get the appropriate parser for a given type.
    
    Args:
        parser_type: The type of parser to get. Use "auto" for auto-detection.
        
    Returns:
        An instance of the appropriate parser.
        
    Raises:
        ParserError: If the parser type is unknown.
    """
    # Lazy imports to avoid circular dependencies
    from flagguard.parsers.launchdarkly import LaunchDarklyParser
    from flagguard.parsers.unleash import UnleashParser
    from flagguard.parsers.generic import GenericParser
    
    parsers: dict[str, type[BaseParser]] = {
        "launchdarkly": LaunchDarklyParser,
        "unleash": UnleashParser,
        "generic": GenericParser,
    }
    
    if parser_type == "auto":
        # Return generic parser, format will be detected from content
        return GenericParser()
    
    if parser_type not in parsers:
        raise ParserError(f"Unknown parser type: {parser_type}")
    
    return parsers[parser_type]()


def parse_config(
    path: Path,
    parser_type: ParserType = "auto",
) -> list[FlagDefinition]:
    """Parse a configuration file.
    
    This is the main entry point for parsing flag configurations.
    It automatically detects the format if not specified.
    
    Args:
        path: Path to the configuration file
        parser_type: Type of parser to use ("auto" for auto-detection)
        
    Returns:
        List of FlagDefinition objects
        
    Raises:
        ParserError: If parsing fails
        FileNotFoundError: If the file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    content = path.read_text(encoding="utf-8")
    
    if parser_type == "auto":
        # Detect format from content
        detected_format = BaseParser.detect_format(content)
        parser = get_parser(detected_format)  # type: ignore
    else:
        parser = get_parser(parser_type)
    
    return parser.parse(content)
