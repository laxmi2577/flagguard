"""JavaScript/TypeScript source code flag extractor.

Extracts feature flag usage patterns from JS/TS source files.
"""

import re
from pathlib import Path
from typing import Any

from flagguard.core.models import FlagUsage
from flagguard.core.logging import get_logger

logger = get_logger("javascript_extractor")


# Common JS/TS flag checking patterns
FLAG_PATTERNS = [
    r"isEnabled\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*\)",
    r"isFeatureEnabled\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*\)",
    r"useFlag\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*\)",
    r"useFeature\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*\)",
    r"variation\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*",
    r"getFlag\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*\)",
    r"hasFeature\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*\)",
    r"checkFeature\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*\)",
    r"flags\s*\[\s*['\"`]([^'\"`]+)['\"`]\s*\]",
    r"client\.variation\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*",
    r"ldClient\.variation\s*\(\s*['\"`]([^'\"`]+)['\"`]\s*",
]


class JavaScriptFlagExtractor:
    """Extracts feature flag usage from JavaScript/TypeScript source code.
    
    Uses regex-based pattern matching. Tree-sitter support can be
    added for more accurate parsing.
    """
    
    def __init__(self) -> None:
        """Initialize the extractor."""
        self._patterns = [re.compile(p) for p in FLAG_PATTERNS]
        self._tree_sitter_available = False
        self._parser: Any = None
        
        # Try to initialize tree-sitter
        try:
            import tree_sitter_javascript as ts_js
            from tree_sitter import Language, Parser
            
            JS_LANGUAGE = Language(ts_js.language())
            self._parser = Parser(JS_LANGUAGE)
            self._tree_sitter_available = True
            logger.debug("tree-sitter JavaScript parser initialized")
        except ImportError:
            logger.debug("tree-sitter not available, using regex fallback")
    
    def extract(self, file_path: Path) -> list[FlagUsage]:
        """Extract flag usages from a JavaScript/TypeScript file.
        
        Args:
            file_path: Path to the JS/TS file
            
        Returns:
            List of FlagUsage objects found
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return []
        
        # For now, use regex extraction (tree-sitter can be added later)
        return self._extract_with_regex(file_path, content)
    
    def _extract_with_regex(
        self,
        file_path: Path,
        content: str,
    ) -> list[FlagUsage]:
        """Extract flags using regex patterns."""
        usages: list[FlagUsage] = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, start=1):
            for pattern in self._patterns:
                for match in pattern.finditer(line):
                    flag_name = match.group(1)
                    
                    # Check if negated
                    negated = self._is_negated(line, match.start())
                    
                    # Try to determine containing function
                    containing_func = self._find_containing_function(
                        lines, line_num - 1
                    )
                    
                    usages.append(FlagUsage(
                        flag_name=flag_name,
                        file_path=str(file_path),
                        line_number=line_num,
                        column=match.start(),
                        containing_function=containing_func,
                        check_type=self._determine_check_type(line),
                        negated=negated,
                        code_snippet=line.strip(),
                    ))
        
        return usages
    
    def _is_negated(self, line: str, match_start: int) -> bool:
        """Check if a flag check is negated."""
        prefix = line[:match_start].rstrip()
        return prefix.endswith("!") or " !" in prefix[-5:] if len(prefix) >= 5 else False
    
    def _determine_check_type(self, line: str) -> str:
        """Determine the type of flag check from context."""
        stripped = line.strip()
        if stripped.startswith("if") or "} else if" in stripped:
            return "if"
        elif "?" in line and ":" in line:
            return "ternary"
        elif "switch" in stripped:
            return "switch"
        elif "=" in line and "==" not in line:
            return "assignment"
        return "expression"
    
    def _find_containing_function(
        self,
        lines: list[str],
        current_line: int,
    ) -> str | None:
        """Find the function containing the current line."""
        # Look backwards for function definitions
        function_patterns = [
            r"function\s+(\w+)\s*\(",
            r"const\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>|\w+\s*=>)",
            r"let\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)",
            r"(\w+)\s*:\s*(?:async\s+)?function\s*\(",
            r"(?:async\s+)?(\w+)\s*\([^)]*\)\s*{",  # Method shorthand
        ]
        
        for i in range(current_line, max(-1, current_line - 100), -1):
            line = lines[i].lstrip()
            for pattern in function_patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(1)
            
            # Stop at class definition
            if line.startswith("class "):
                break
        
        return None
