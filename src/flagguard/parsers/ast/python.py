"""Python source code flag extractor using tree-sitter.

Extracts feature flag usage patterns from Python source files.
"""

import re
from pathlib import Path
from typing import Any

from flagguard.core.models import FlagUsage
from flagguard.core.logging import get_logger

logger = get_logger("python_extractor")


# Common flag checking function patterns
FLAG_PATTERNS = [
    r"is_enabled\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    r"is_feature_enabled\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    r"feature_enabled\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    r"variation\s*\(\s*['\"]([^'\"]+)['\"]\s*",
    r"get_flag\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    r"has_feature\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    r"check_feature\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    r"flags\s*\[\s*['\"]([^'\"]+)['\"]\s*\]",
    r"feature_flags\.([a-zA-Z_][a-zA-Z0-9_]*)",
]


class PythonFlagExtractor:
    """Extracts feature flag usage from Python source code.
    
    Uses regex-based pattern matching as a fallback when tree-sitter
    is not available. When tree-sitter is available, uses AST parsing
    for more accurate extraction.
    """
    
    def __init__(self) -> None:
        """Initialize the extractor."""
        self._patterns = [re.compile(p) for p in FLAG_PATTERNS]
        self._tree_sitter_available = False
        self._parser: Any = None
        
        # Try to initialize tree-sitter
        try:
            import tree_sitter_python as ts_python
            from tree_sitter import Language, Parser
            
            PY_LANGUAGE = Language(ts_python.language())
            self._parser = Parser(PY_LANGUAGE)
            self._tree_sitter_available = True
            logger.debug("tree-sitter Python parser initialized")
        except ImportError:
            logger.debug("tree-sitter not available, using regex fallback")
    
    def extract(self, file_path: Path) -> list[FlagUsage]:
        """Extract flag usages from a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of FlagUsage objects found
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return []
        
        if self._tree_sitter_available:
            return self._extract_with_tree_sitter(file_path, content)
        else:
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
                        check_type="if",  # Simplified
                        negated=negated,
                        code_snippet=line.strip(),
                    ))
        
        return usages
    
    def _extract_with_tree_sitter(
        self,
        file_path: Path,
        content: str,
    ) -> list[FlagUsage]:
        """Extract flags using tree-sitter AST parsing."""
        if not self._parser:
            return self._extract_with_regex(file_path, content)
        
        tree = self._parser.parse(bytes(content, "utf-8"))
        usages: list[FlagUsage] = []
        
        # Query for function calls
        self._traverse_tree(
            tree.root_node,
            file_path,
            content,
            usages,
        )
        
        return usages
    
    def _traverse_tree(
        self,
        node: Any,
        file_path: Path,
        content: str,
        usages: list[FlagUsage],
        context: dict[str, str | None] | None = None,
    ) -> None:
        """Traverse AST and extract flag usages."""
        if context is None:
            context = {"function": None, "class": None}
        
        # Update context for function/class definitions
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                context = {**context, "function": name_node.text.decode("utf-8")}
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                context = {**context, "class": name_node.text.decode("utf-8")}
        
        # Check for function calls
        if node.type == "call":
            usage = self._extract_from_call(node, file_path, content, context)
            if usage:
                usages.append(usage)
        
        # Recurse into children
        for child in node.children:
            self._traverse_tree(child, file_path, content, usages, context)
    
    def _extract_from_call(
        self,
        node: Any,
        file_path: Path,
        content: str,
        context: dict[str, str | None],
    ) -> FlagUsage | None:
        """Extract flag usage from a function call node."""
        func_node = node.child_by_field_name("function")
        if not func_node:
            return None
        
        func_text = func_node.text.decode("utf-8")
        
        # Check if this is a flag-checking function
        flag_funcs = [
            "is_enabled", "is_feature_enabled", "feature_enabled",
            "variation", "get_flag", "has_feature", "check_feature",
        ]
        
        func_name = func_text.split(".")[-1]  # Handle method calls
        if func_name not in flag_funcs:
            return None
        
        # Get the first argument (flag name)
        args_node = node.child_by_field_name("arguments")
        if not args_node or len(args_node.children) < 2:
            return None
        
        # Find string argument
        for child in args_node.children:
            if child.type == "string":
                flag_name = child.text.decode("utf-8").strip("'\"")
                
                # Get line content
                lines = content.splitlines()
                line_content = lines[node.start_point[0]] if lines else ""
                
                # Check for negation
                negated = self._check_negation_in_ast(node)
                
                return FlagUsage(
                    flag_name=flag_name,
                    file_path=str(file_path),
                    line_number=node.start_point[0] + 1,
                    column=node.start_point[1],
                    end_line=node.end_point[0] + 1,
                    end_column=node.end_point[1],
                    containing_function=context.get("function"),
                    containing_class=context.get("class"),
                    check_type=self._determine_check_type(node),
                    negated=negated,
                    code_snippet=line_content.strip(),
                )
        
        return None
    
    def _is_negated(self, line: str, match_start: int) -> bool:
        """Check if a flag check is negated."""
        prefix = line[:match_start].rstrip()
        return prefix.endswith("not ") or prefix.endswith("!")
    
    def _check_negation_in_ast(self, node: Any) -> bool:
        """Check if node is inside a not expression."""
        parent = node.parent
        while parent:
            if parent.type == "not_operator":
                return True
            parent = parent.parent
        return False
    
    def _determine_check_type(self, node: Any) -> str:
        """Determine the type of flag check."""
        parent = node.parent
        while parent:
            if parent.type == "if_statement":
                return "if"
            elif parent.type == "conditional_expression":
                return "ternary"
            elif parent.type == "assignment":
                return "assignment"
            elif parent.type == "match_statement":
                return "match"
            parent = parent.parent
        return "expression"
    
    def _find_containing_function(
        self,
        lines: list[str],
        current_line: int,
    ) -> str | None:
        """Find the function containing the current line."""
        # Simple heuristic: look backwards for 'def '
        for i in range(current_line, -1, -1):
            line = lines[i].lstrip()
            if line.startswith("def "):
                # Extract function name
                match = re.match(r"def\s+(\w+)\s*\(", line)
                if match:
                    return match.group(1)
            elif line.startswith("class "):
                # We've gone past the function into class level
                break
        return None
