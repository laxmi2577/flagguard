"""Language configuration for AST parsing.

This module provides a registry of supported programming languages
and their parsing configurations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from flagguard.core.logging import get_logger

logger = get_logger("languages")


class SupportedLanguage(Enum):
    """Languages supported by FlagGuard AST parsing."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


@dataclass
class LanguageConfig:
    """Configuration for a supported language.
    
    Attributes:
        name: Human-readable language name
        extensions: File extensions for this language
        flag_function_names: Names of functions that check flags
        flag_method_names: Names of methods that check flags
        language_factory: Factory function to create tree-sitter Language
    """
    name: str
    extensions: list[str]
    flag_function_names: set[str]
    flag_method_names: set[str]
    language_factory: Callable[[], Any] | None = None
    
    def get_language(self) -> Any:
        """Get the tree-sitter Language object.
        
        Returns:
            tree-sitter Language object or None if not available
        """
        if self.language_factory:
            try:
                return self.language_factory()
            except Exception as e:
                logger.debug(f"Failed to load {self.name} language: {e}")
        return None


def _create_python_language() -> Any:
    """Create Python tree-sitter language."""
    import tree_sitter_python as ts_python
    from tree_sitter import Language
    return Language(ts_python.language())


def _create_javascript_language() -> Any:
    """Create JavaScript tree-sitter language."""
    import tree_sitter_javascript as ts_javascript
    from tree_sitter import Language
    return Language(ts_javascript.language())


def _create_typescript_language() -> Any:
    """Create TypeScript tree-sitter language."""
    import tree_sitter_typescript as ts_typescript
    from tree_sitter import Language
    return Language(ts_typescript.language_typescript())


# Common flag checking function names
PYTHON_FLAG_FUNCTIONS = {
    "is_enabled", "is_feature_enabled", "feature_enabled",
    "variation", "get_flag", "has_feature", "check_feature",
    "is_on", "is_active", "get_feature_flag",
}

PYTHON_FLAG_METHODS = {
    "is_enabled", "is_feature_enabled", "variation",
    "get_variation", "evaluate", "is_on", "get",
    "is_active", "feature_value", "get_flag",
}

JS_FLAG_METHODS = {
    "isEnabled", "isFeatureEnabled", "variation",
    "getVariation", "evaluate", "isOn", "get",
    "isActive", "hasFeature", "getFlag",
}

# Language registry
LANGUAGE_REGISTRY: dict[SupportedLanguage, LanguageConfig] = {
    SupportedLanguage.PYTHON: LanguageConfig(
        name="Python",
        extensions=[".py", ".pyw"],
        flag_function_names=PYTHON_FLAG_FUNCTIONS,
        flag_method_names=PYTHON_FLAG_METHODS,
        language_factory=_create_python_language,
    ),
    SupportedLanguage.JAVASCRIPT: LanguageConfig(
        name="JavaScript",
        extensions=[".js", ".jsx", ".mjs", ".cjs"],
        flag_function_names=set(),  # JS typically uses method calls
        flag_method_names=JS_FLAG_METHODS,
        language_factory=_create_javascript_language,
    ),
    SupportedLanguage.TYPESCRIPT: LanguageConfig(
        name="TypeScript",
        extensions=[".ts", ".tsx", ".mts", ".cts"],
        flag_function_names=set(),
        flag_method_names=JS_FLAG_METHODS,
        language_factory=_create_typescript_language,
    ),
}


def get_language_for_file(file_path: str) -> SupportedLanguage | None:
    """Determine the programming language based on file extension.
    
    Args:
        file_path: Path to the source file
        
    Returns:
        SupportedLanguage enum value or None if unsupported
    """
    # Extract extension
    ext = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    
    for lang, config in LANGUAGE_REGISTRY.items():
        if ext in config.extensions:
            return lang
    
    return None


def get_config_for_language(lang: SupportedLanguage) -> LanguageConfig:
    """Get the configuration for a language.
    
    Args:
        lang: The language to get config for
        
    Returns:
        LanguageConfig for the language
    """
    return LANGUAGE_REGISTRY[lang]


def get_supported_extensions() -> list[str]:
    """Get all supported file extensions.
    
    Returns:
        List of all file extensions we can parse
    """
    extensions = []
    for config in LANGUAGE_REGISTRY.values():
        extensions.extend(config.extensions)
    return extensions
