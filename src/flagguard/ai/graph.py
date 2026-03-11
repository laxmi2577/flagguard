"""Knowledge Graph builder for FlagGuard GraphRAG.

Constructs a directed call graph from tree-sitter AST to map which
functions call which other functions, and which flags guard them.
Used alongside ChromaDB vector search in the Hybrid Retriever.

Skills demonstrated: Graph Theory, NetworkX, AST Traversal, Knowledge Graphs.
"""

from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

import networkx as nx

from flagguard.core.logging import get_logger
from flagguard.rag.ingester import ASTCodeChunker, FLAG_CHECK_PATTERNS

logger = get_logger("ai.graph")


@dataclass
class FunctionNode:
    """Metadata for a function node in the call graph."""
    qualified_name: str
    file_path: str
    start_line: int
    end_line: int
    flags_referenced: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)


class CodeKnowledgeGraph:
    """Builds and queries a directed call graph of a codebase.

    The graph has function/method nodes with edges representing
    "function A calls function B". Each node stores metadata about
    which feature flags are referenced inside that function.

    This enables transitive impact analysis: when Flag X has a conflict,
    we can traverse the graph to find ALL functions that transitively
    depend on Flag X, not just the ones that directly check it.

    Usage:
        >>> graph = CodeKnowledgeGraph()
        >>> graph.build_from_directory(Path("./src"))
        >>> affected = graph.get_transitive_callers("premium_checkout")
        >>> flag_funcs = graph.get_functions_using_flag("dark_mode")
    """

    SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}
    EXCLUDE_DIRS = {
        "node_modules", "venv", ".venv", "__pycache__", ".git",
        "dist", "build", ".mypy_cache", ".pytest_cache",
    }

    def __init__(self):
        self.graph = nx.DiGraph()
        self._function_registry: dict[str, FunctionNode] = {}
        self._py_parser: Any = None
        self._js_parser: Any = None
        self._init_parsers()

    def _init_parsers(self):
        """Initialize tree-sitter parsers."""
        try:
            import tree_sitter_python as ts_python
            from tree_sitter import Language, Parser
            py_lang = Language(ts_python.language())
            self._py_parser = Parser(py_lang)
        except (ImportError, Exception):
            logger.warning("Python tree-sitter unavailable for graph building")

        try:
            import tree_sitter_javascript as ts_js
            from tree_sitter import Language, Parser
            js_lang = Language(ts_js.language())
            self._js_parser = Parser(js_lang)
        except (ImportError, Exception):
            logger.warning("JS tree-sitter unavailable for graph building")

    def build_from_directory(self, root: Path) -> int:
        """Build the knowledge graph from a source directory.

        Args:
            root: Root directory of the codebase.

        Returns:
            Number of function nodes added to the graph.
        """
        logger.info(f"Building knowledge graph from {root}")

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue
            if any(ex in file_path.parts for ex in self.EXCLUDE_DIRS):
                continue

            try:
                self._process_file(file_path, root)
            except Exception as e:
                logger.warning(f"Failed to process {file_path} for graph: {e}")

        # Second pass: resolve call edges
        self._resolve_call_edges()

        logger.info(
            f"Knowledge graph built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )
        return self.graph.number_of_nodes()

    def _process_file(self, file_path: Path, root: Path):
        """Process a single file: extract functions and their calls."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if not content.strip():
            return

        rel_path = file_path.relative_to(root).as_posix()
        parser = self._get_parser(file_path.suffix)

        if not parser:
            return

        tree = parser.parse(bytes(content, "utf-8"))
        lines = content.splitlines()

        self._extract_functions_and_calls(
            node=tree.root_node,
            file_path=rel_path,
            lines=lines,
            content=content,
            current_class=None,
        )

    def _get_parser(self, suffix: str) -> Any | None:
        if suffix == ".py":
            return self._py_parser
        elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
            return self._js_parser
        return None

    def _extract_functions_and_calls(
        self,
        node: Any,
        file_path: str,
        lines: list[str],
        content: str,
        current_class: str | None,
        current_function: str | None = None,
    ):
        """Walk AST to extract function definitions and the calls they make."""
        import re

        # Track function/method definitions
        if node.type in ("function_definition", "function_declaration", "method_definition"):
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = name_node.text.decode("utf-8")
                qualified = f"{current_class}.{func_name}" if current_class else func_name

                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                func_text = "\n".join(lines[start_line - 1:end_line])

                # Extract flag references from this function
                flags: list[str] = []
                for pattern_name in FLAG_CHECK_PATTERNS:
                    pattern = rf'{re.escape(pattern_name)}\s*\(\s*["\']([^"\']+)["\']'
                    for match in re.finditer(pattern, func_text):
                        flags.append(match.group(1))

                # Extract function calls from this function body
                calls = self._extract_calls_from_node(node)

                func_node = FunctionNode(
                    qualified_name=qualified,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    flags_referenced=list(set(flags)),
                    calls=calls,
                )

                self._function_registry[qualified] = func_node
                self.graph.add_node(qualified, **{
                    "file_path": file_path,
                    "start_line": start_line,
                    "end_line": end_line,
                    "flags": list(set(flags)),
                })

                # Recurse into function body with updated context
                for child in node.children:
                    self._extract_functions_and_calls(
                        child, file_path, lines, content,
                        current_class, qualified,
                    )
                return

        # Track class definitions
        if node.type in ("class_definition", "class_declaration"):
            name_node = node.child_by_field_name("name")
            class_name = name_node.text.decode("utf-8") if name_node else None
            for child in node.children:
                self._extract_functions_and_calls(
                    child, file_path, lines, content,
                    class_name, current_function,
                )
            return

        # Recurse for all other node types
        for child in node.children:
            self._extract_functions_and_calls(
                child, file_path, lines, content,
                current_class, current_function,
            )

    def _extract_calls_from_node(self, node: Any) -> list[str]:
        """Extract all function call names from inside a node."""
        calls: list[str] = []

        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                call_name = func_node.text.decode("utf-8")
                # Normalize: extract last part of dotted calls
                simple_name = call_name.split(".")[-1]
                calls.append(simple_name)

        for child in node.children:
            calls.extend(self._extract_calls_from_node(child))

        return calls

    def _resolve_call_edges(self):
        """Create edges between caller and callee nodes."""
        known_functions = set(self.graph.nodes())
        # Also build a simple-name → qualified-name lookup
        simple_to_qualified: dict[str, list[str]] = {}
        for qname in known_functions:
            simple = qname.split(".")[-1]
            simple_to_qualified.setdefault(simple, []).append(qname)

        for qname, func_node in self._function_registry.items():
            for call_name in func_node.calls:
                # Try exact match first
                if call_name in known_functions:
                    if call_name != qname:  # no self-edges
                        self.graph.add_edge(qname, call_name)
                # Then try simple name resolution
                elif call_name in simple_to_qualified:
                    for target in simple_to_qualified[call_name]:
                        if target != qname:
                            self.graph.add_edge(qname, target)

    # ── Query Methods ──

    def get_functions_using_flag(self, flag_name: str) -> list[FunctionNode]:
        """Find all functions that directly reference a given flag.

        Args:
            flag_name: The feature flag name to search for.

        Returns:
            List of FunctionNode objects that check this flag.
        """
        results = []
        for qname, data in self.graph.nodes(data=True):
            if flag_name in data.get("flags", []):
                if qname in self._function_registry:
                    results.append(self._function_registry[qname])
        return results

    def get_transitive_callers(self, function_name: str) -> list[FunctionNode]:
        """Find all functions that transitively call a given function.

        Uses reverse BFS on the directed graph to find all ancestors
        (i.e., all functions where execution could flow down to the target).

        Args:
            function_name: The target function name.

        Returns:
            List of FunctionNode objects that are upstream callers.
        """
        # Find matching nodes (support simple or qualified names)
        target_nodes = []
        for node in self.graph.nodes():
            if node == function_name or node.endswith(f".{function_name}"):
                target_nodes.append(node)

        callers = set()
        for target in target_nodes:
            # nx.ancestors gives all nodes with a path TO the target
            try:
                ancestors = nx.ancestors(self.graph, target)
                callers.update(ancestors)
            except nx.NetworkXError:
                pass

        results = []
        for caller in callers:
            if caller in self._function_registry:
                results.append(self._function_registry[caller])
        return results

    def get_impact_for_flag(self, flag_name: str) -> list[FunctionNode]:
        """Find ALL functions impacted by a flag conflict (direct + transitive).

        This is the core GraphRAG query: when Z3 finds a conflict for a flag,
        this method returns every function that could be affected.

        Args:
            flag_name: The conflicting feature flag name.

        Returns:
            Deduplicated list of all impacted FunctionNode objects.
        """
        # 1. Find direct users of the flag
        direct_users = self.get_functions_using_flag(flag_name)

        # 2. Find all transitive callers of those functions
        all_impacted: dict[str, FunctionNode] = {}
        for user in direct_users:
            all_impacted[user.qualified_name] = user
            callers = self.get_transitive_callers(user.qualified_name)
            for caller in callers:
                all_impacted[caller.qualified_name] = caller

        return list(all_impacted.values())

    def get_graph_stats(self) -> dict[str, Any]:
        """Return graph statistics for debugging and UI display."""
        return {
            "total_functions": self.graph.number_of_nodes(),
            "total_call_edges": self.graph.number_of_edges(),
            "connected_components": nx.number_weakly_connected_components(self.graph),
            "functions_with_flags": sum(
                1 for _, data in self.graph.nodes(data=True)
                if data.get("flags")
            ),
            "avg_degree": (
                sum(dict(self.graph.degree()).values()) / max(self.graph.number_of_nodes(), 1)
            ),
        }
