"""AST parsing module for flag extraction from source code.

This module provides source code scanning capabilities using
tree-sitter for multi-language AST parsing.
"""

from flagguard.parsers.ast.scanner import SourceScanner
from flagguard.parsers.ast.python import PythonFlagExtractor
from flagguard.parsers.ast.javascript import JavaScriptFlagExtractor
from flagguard.parsers.ast.languages import (
    SupportedLanguage,
    LanguageConfig,
    LANGUAGE_REGISTRY,
    get_language_for_file,
    get_config_for_language,
    get_supported_extensions,
)

__all__ = [
    "SourceScanner",
    "PythonFlagExtractor",
    "JavaScriptFlagExtractor",
    "SupportedLanguage",
    "LanguageConfig",
    "LANGUAGE_REGISTRY",
    "get_language_for_file",
    "get_config_for_language",
    "get_supported_extensions",
]

