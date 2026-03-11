"""Hybrid RAG Retriever for FlagGuard GraphRAG.

Combines two retrieval strategies for maximum context quality:
1. Semantic Search (ChromaDB) — finds code chunks by meaning similarity.
2. Graph Traversal (NetworkX) — finds all transitively impacted functions.

The results are merged, deduplicated, and ranked before being passed
to the LLM for conflict explanation and code-fix generation.

Skills demonstrated: Hybrid Search, Vector Databases, Knowledge Graphs, RAG.
"""

from pathlib import Path
from typing import Any
from dataclasses import dataclass

from flagguard.core.logging import get_logger
from flagguard.rag.store import VectorStore, Document
from flagguard.rag.embeddings import get_embeddings_provider

logger = get_logger("rag.retriever")


@dataclass
class RetrievalResult:
    """A single retrieved context item with source attribution."""
    text: str
    file_path: str
    function_name: str
    start_line: int
    end_line: int
    source: str  # "semantic", "graph", or "both"
    relevance_score: float = 0.0


class HybridRetriever:
    """Combines ChromaDB vector search with Knowledge Graph traversal.

    This is the core of the GraphRAG architecture. When a flag conflict
    is detected, the retriever:
    1. Queries ChromaDB for semantically similar code chunks.
    2. Queries the Knowledge Graph for all transitively impacted functions.
    3. Merges, deduplicates, and ranks the results.

    Usage:
        >>> retriever = HybridRetriever(workspace_path="./src")
        >>> results = retriever.retrieve_for_conflict(
        ...     flag_names=["premium", "payment_system"],
        ...     conflict_description="premium requires payment_system but it is disabled",
        ... )
    """

    def __init__(
        self,
        workspace_path: str | None = None,
        use_graph: bool = True,
    ):
        self.store = VectorStore()
        self.embeddings = get_embeddings_provider(use_ollama=True)
        self._graph = None
        self._use_graph = use_graph

        if use_graph and workspace_path:
            self._init_graph(Path(workspace_path))

    def _init_graph(self, workspace: Path):
        """Lazily initialize the Knowledge Graph."""
        try:
            from flagguard.ai.graph import CodeKnowledgeGraph
            self._graph = CodeKnowledgeGraph()
            node_count = self._graph.build_from_directory(workspace)
            logger.info(f"Knowledge Graph initialized with {node_count} nodes")
        except Exception as e:
            logger.warning(f"Knowledge Graph unavailable: {e}")
            self._graph = None

    def retrieve(self, query: str, top_k: int = 5) -> list[Document]:
        """Simple semantic retrieval (backwards compatible).

        Args:
            query: User question or search query.
            top_k: Number of results to return.

        Returns:
            List of relevant Documents from ChromaDB.
        """
        if self.store.count() == 0:
            logger.warning("Vector store is empty. Please index the codebase first.")
            return []

        query_embedding = self.embeddings.embed_query(query)
        if not query_embedding:
            return []

        return self.store.query(query_embedding, n_results=top_k)

    def retrieve_for_conflict(
        self,
        flag_names: list[str],
        conflict_description: str,
        top_k_semantic: int = 5,
        top_k_graph: int = 10,
    ) -> list[RetrievalResult]:
        """Hybrid retrieval optimized for flag conflict remediation.

        Combines semantic search (what code LOOKS like it's related) with
        graph traversal (what code IS mathematically connected).

        Args:
            flag_names: List of conflicting flag names.
            conflict_description: Human-readable conflict description.
            top_k_semantic: Max results from ChromaDB.
            top_k_graph: Max results from Knowledge Graph.

        Returns:
            Merged, deduplicated, ranked list of RetrievalResults.
        """
        results: dict[str, RetrievalResult] = {}

        # ── Strategy 1: Semantic Search (ChromaDB) ──
        semantic_results = self._semantic_search(
            flag_names, conflict_description, top_k_semantic
        )
        for r in semantic_results:
            key = f"{r.file_path}:{r.start_line}"
            r.source = "semantic"
            results[key] = r

        # ── Strategy 2: Graph Traversal (NetworkX) ──
        if self._graph and self._use_graph:
            graph_results = self._graph_search(flag_names, top_k_graph)
            for r in graph_results:
                key = f"{r.file_path}:{r.start_line}"
                if key in results:
                    # Exists in both → boost relevance and mark as "both"
                    results[key].source = "both"
                    results[key].relevance_score += 0.3
                else:
                    r.source = "graph"
                    results[key] = r

        # ── Rank and Return ──
        ranked = sorted(
            results.values(),
            key=lambda r: (
                # Priority: "both" > "semantic" > "graph"
                {"both": 3, "semantic": 2, "graph": 1}.get(r.source, 0),
                r.relevance_score,
            ),
            reverse=True,
        )

        total = top_k_semantic + top_k_graph
        final = ranked[:total]
        logger.info(
            f"Hybrid retrieval: {len(semantic_results)} semantic + "
            f"{len(graph_results) if self._graph else 0} graph → "
            f"{len(final)} merged results"
        )
        return final

    def _semantic_search(
        self,
        flag_names: list[str],
        conflict_description: str,
        top_k: int,
    ) -> list[RetrievalResult]:
        """Retrieve via ChromaDB vector similarity."""
        if self.store.count() == 0:
            return []

        # Build a rich query combining flag names and conflict context
        query = (
            f"Feature flag conflict: {', '.join(flag_names)}. "
            f"{conflict_description}"
        )

        query_embedding = self.embeddings.embed_query(query)
        if not query_embedding:
            return []

        docs = self.store.query(query_embedding, n_results=top_k)
        results = []
        for doc in docs:
            results.append(RetrievalResult(
                text=doc.text,
                file_path=doc.metadata.get("file", "unknown"),
                function_name=doc.metadata.get("function_name", ""),
                start_line=int(doc.metadata.get("start_line", 0)),
                end_line=int(doc.metadata.get("end_line", 0)),
                source="semantic",
                relevance_score=0.5,
            ))
        return results

    def _graph_search(
        self,
        flag_names: list[str],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Retrieve via Knowledge Graph transitive impact analysis."""
        if not self._graph:
            return []

        results = []
        seen = set()

        for flag_name in flag_names:
            impacted = self._graph.get_impact_for_flag(flag_name)
            for func_node in impacted:
                if func_node.qualified_name in seen:
                    continue
                seen.add(func_node.qualified_name)

                # Read the actual source code for this function
                text = self._read_function_source(func_node)

                results.append(RetrievalResult(
                    text=text,
                    file_path=func_node.file_path,
                    function_name=func_node.qualified_name,
                    start_line=func_node.start_line,
                    end_line=func_node.end_line,
                    source="graph",
                    relevance_score=0.4,
                ))

        return results[:top_k]

    def _read_function_source(self, func_node: Any) -> str:
        """Read source code lines for a function from disk."""
        try:
            # Try to find the file from either the workspace or as-is
            file_path = Path(func_node.file_path)
            if not file_path.exists():
                return f"[Source unavailable for {func_node.qualified_name}]"

            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            start = max(0, func_node.start_line - 1)
            end = min(len(lines), func_node.end_line)
            source = "\n".join(lines[start:end])

            return (
                f"File: {func_node.file_path} | "
                f"Function: {func_node.qualified_name} | "
                f"Lines: {func_node.start_line}-{func_node.end_line}\n\n"
                f"{source}"
            )
        except Exception:
            return f"[Source unavailable for {func_node.qualified_name}]"

    def format_context_for_llm(self, results: list[RetrievalResult]) -> str:
        """Format retrieval results into a single context string for the LLM.

        Args:
            results: List of RetrievalResult from hybrid retrieval.

        Returns:
            Formatted context string ready for prompt injection.
        """
        if not results:
            return "No relevant source code context found."

        sections = []
        for i, r in enumerate(results, 1):
            source_tag = f"[{r.source.upper()}]"
            header = (
                f"--- Context #{i} {source_tag} ---\n"
                f"File: {r.file_path}"
            )
            if r.function_name:
                header += f" | Function: {r.function_name}"
            header += f" | Lines: {r.start_line}-{r.end_line}"

            sections.append(f"{header}\n{r.text}")

        return "\n\n".join(sections)


# Backwards-compatible alias
class CheckRetriever:
    """Legacy retriever interface (backwards compatible with existing code)."""

    def __init__(self):
        self._hybrid = HybridRetriever(use_graph=False)

    def retrieve(self, query: str, top_k: int = 5) -> list[Document]:
        return self._hybrid.retrieve(query, top_k)
