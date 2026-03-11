"""AST-aware codebase ingester for FlagGuard RAG.

Replaces the naive line-based chunker with a tree-sitter AST walker
that extracts individual functions/classes as semantic chunks,
dramatically improving retrieval quality for conflict remediation.
"""

import hashlib
from pathlib import Path
from typing import Any

from flagguard.core.logging import get_logger
from flagguard.parsers.factory import parse_config
from flagguard.rag.store import Document, VectorStore
from flagguard.rag.embeddings import get_embeddings_provider

logger = get_logger("rag.ingester")

# Flag-checking function names to tag in metadata
FLAG_CHECK_PATTERNS = {
    "is_enabled", "is_feature_enabled", "feature_enabled",
    "variation", "get_flag", "has_feature", "check_feature",
    "isEnabled", "isFeatureEnabled", "featureEnabled",
    "getFlag", "hasFeature", "checkFeature",
}


class ASTChunk:
    """Represents a semantic chunk extracted from source code AST."""

    def __init__(
        self,
        text: str,
        file_path: str,
        function_name: str | None,
        class_name: str | None,
        start_line: int,
        end_line: int,
        flags_referenced: list[str],
        chunk_type: str = "function",
    ):
        self.text = text
        self.file_path = file_path
        self.function_name = function_name
        self.class_name = class_name
        self.start_line = start_line
        self.end_line = end_line
        self.flags_referenced = flags_referenced
        self.chunk_type = chunk_type

    @property
    def qualified_name(self) -> str:
        """Return fully qualified name like 'ClassName.method_name'."""
        parts = []
        if self.class_name:
            parts.append(self.class_name)
        if self.function_name:
            parts.append(self.function_name)
        return ".".join(parts) if parts else f"<module>:{self.start_line}"

    @property
    def doc_id(self) -> str:
        """Generate a stable document ID for ChromaDB."""
        raw = f"{self.file_path}:{self.qualified_name}:{self.start_line}"
        return hashlib.md5(raw.encode()).hexdigest()


class ASTCodeChunker:
    """Extracts function-level and class-level chunks using tree-sitter AST."""

    def __init__(self):
        self._py_parser: Any = None
        self._js_parser: Any = None
        self._init_parsers()

    def _init_parsers(self):
        """Initialize tree-sitter parsers for Python and JavaScript."""
        try:
            import tree_sitter_python as ts_python
            from tree_sitter import Language, Parser

            py_lang = Language(ts_python.language())
            self._py_parser = Parser(py_lang)
            logger.debug("tree-sitter Python parser ready for AST chunking")
        except (ImportError, Exception) as e:
            logger.warning(f"Python tree-sitter unavailable for chunking: {e}")

        try:
            import tree_sitter_javascript as ts_js
            from tree_sitter import Language, Parser

            js_lang = Language(ts_js.language())
            self._js_parser = Parser(js_lang)
            logger.debug("tree-sitter JavaScript parser ready for AST chunking")
        except (ImportError, Exception) as e:
            logger.warning(f"JavaScript tree-sitter unavailable for chunking: {e}")

    def chunk_file(self, file_path: Path) -> list[ASTChunk]:
        """Extract AST-aware chunks from a single source file.

        Args:
            file_path: Path to the source file.

        Returns:
            List of ASTChunk objects, one per function/class/module-level block.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Cannot read {file_path}: {e}")
            return []

        if not content.strip():
            return []

        parser = self._get_parser(file_path.suffix)
        if parser:
            return self._chunk_with_ast(parser, file_path, content)
        else:
            return self._chunk_fallback(file_path, content)

    def _get_parser(self, suffix: str) -> Any | None:
        """Get the appropriate tree-sitter parser for a file extension."""
        if suffix == ".py":
            return self._py_parser
        elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
            return self._js_parser
        return None

    def _chunk_with_ast(
        self, parser: Any, file_path: Path, content: str
    ) -> list[ASTChunk]:
        """Extract chunks using tree-sitter AST parsing."""
        tree = parser.parse(bytes(content, "utf-8"))
        chunks: list[ASTChunk] = []
        lines = content.splitlines()

        self._walk_node(
            node=tree.root_node,
            file_path=str(file_path),
            lines=lines,
            content=content,
            chunks=chunks,
            current_class=None,
        )

        # If no functions/classes found, treat entire file as one chunk
        if not chunks and len(lines) > 0:
            flags = self._extract_flag_refs(content)
            chunks.append(ASTChunk(
                text=content,
                file_path=str(file_path),
                function_name=None,
                class_name=None,
                start_line=1,
                end_line=len(lines),
                flags_referenced=flags,
                chunk_type="module",
            ))

        return chunks

    def _walk_node(
        self,
        node: Any,
        file_path: str,
        lines: list[str],
        content: str,
        chunks: list[ASTChunk],
        current_class: str | None,
    ):
        """Recursively walk AST nodes to extract function and class chunks."""
        # Python function definitions
        if node.type in ("function_definition", "decorated_definition"):
            actual_node = node
            if node.type == "decorated_definition":
                # Find the actual function_definition inside decorators
                for child in node.children:
                    if child.type == "function_definition":
                        actual_node = child
                        break

            func_name_node = actual_node.child_by_field_name("name")
            func_name = func_name_node.text.decode("utf-8") if func_name_node else None

            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            func_text = "\n".join(lines[start_line - 1:end_line])
            flags = self._extract_flag_refs(func_text)

            chunks.append(ASTChunk(
                text=func_text,
                file_path=file_path,
                function_name=func_name,
                class_name=current_class,
                start_line=start_line,
                end_line=end_line,
                flags_referenced=flags,
                chunk_type="method" if current_class else "function",
            ))
            return  # Don't recurse into function body (already captured)

        # JavaScript/TypeScript function variants
        if node.type in (
            "function_declaration", "arrow_function",
            "method_definition", "generator_function_declaration",
        ):
            func_name = None
            func_name_node = node.child_by_field_name("name")
            if func_name_node:
                func_name = func_name_node.text.decode("utf-8")
            elif node.parent and node.parent.type == "variable_declarator":
                name_node = node.parent.child_by_field_name("name")
                if name_node:
                    func_name = name_node.text.decode("utf-8")

            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            func_text = "\n".join(lines[start_line - 1:end_line])
            flags = self._extract_flag_refs(func_text)

            chunks.append(ASTChunk(
                text=func_text,
                file_path=file_path,
                function_name=func_name,
                class_name=current_class,
                start_line=start_line,
                end_line=end_line,
                flags_referenced=flags,
                chunk_type="method" if current_class else "function",
            ))
            return

        # Class definitions (Python and JS)
        if node.type in ("class_definition", "class_declaration"):
            class_name_node = node.child_by_field_name("name")
            class_name = class_name_node.text.decode("utf-8") if class_name_node else None

            # Recurse into class body with class context
            for child in node.children:
                self._walk_node(
                    node=child,
                    file_path=file_path,
                    lines=lines,
                    content=content,
                    chunks=chunks,
                    current_class=class_name,
                )
            return

        # Recurse into other nodes
        for child in node.children:
            self._walk_node(
                node=child,
                file_path=file_path,
                lines=lines,
                content=content,
                chunks=chunks,
                current_class=current_class,
            )

    def _extract_flag_refs(self, text: str) -> list[str]:
        """Extract flag names referenced in a text block."""
        import re
        flags = set()
        for pattern_name in FLAG_CHECK_PATTERNS:
            # Match function_name("flag_name") or function_name('flag_name')
            pattern = rf'{re.escape(pattern_name)}\s*\(\s*["\']([^"\']+)["\']'
            for match in re.finditer(pattern, text):
                flags.add(match.group(1))
        return sorted(flags)

    def _chunk_fallback(self, file_path: Path, content: str) -> list[ASTChunk]:
        """Fallback chunker when tree-sitter is unavailable.

        Uses function-level regex detection for Python,
        and 40-line sliding window for other languages.
        """
        import re
        lines = content.splitlines()
        chunks: list[ASTChunk] = []

        # Try Python function detection via regex
        if file_path.suffix == ".py":
            func_pattern = re.compile(r"^(class |def )", re.MULTILINE)
            boundaries = [m.start() for m in func_pattern.finditer(content)]
            boundaries.append(len(content))

            for i in range(len(boundaries) - 1):
                chunk_text = content[boundaries[i]:boundaries[i + 1]].strip()
                if not chunk_text:
                    continue

                start_line = content[:boundaries[i]].count("\n") + 1
                end_line = start_line + chunk_text.count("\n")
                flags = self._extract_flag_refs(chunk_text)

                # Extract name
                name_match = re.match(r"(?:class|def)\s+(\w+)", chunk_text)
                name = name_match.group(1) if name_match else None
                is_class = chunk_text.startswith("class ")

                chunks.append(ASTChunk(
                    text=chunk_text,
                    file_path=str(file_path),
                    function_name=None if is_class else name,
                    class_name=name if is_class else None,
                    start_line=start_line,
                    end_line=end_line,
                    flags_referenced=flags,
                    chunk_type="class" if is_class else "function",
                ))

        # Sliding window fallback for non-Python files
        if not chunks:
            chunk_size = 40
            overlap = 10
            for i in range(0, len(lines), chunk_size - overlap):
                chunk_lines = lines[i:i + chunk_size]
                if not chunk_lines:
                    continue
                chunk_text = "\n".join(chunk_lines)
                flags = self._extract_flag_refs(chunk_text)
                start_line = i + 1
                end_line = i + len(chunk_lines)

                chunks.append(ASTChunk(
                    text=chunk_text,
                    file_path=str(file_path),
                    function_name=None,
                    class_name=None,
                    start_line=start_line,
                    end_line=end_line,
                    flags_referenced=flags,
                    chunk_type="block",
                ))

        return chunks


class CodebaseIngester:
    """Ingests codebase and flags into the vector store using AST-aware chunking."""

    SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}
    EXCLUDE_DIRS = {
        "node_modules", "venv", ".venv", "__pycache__", ".git",
        "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    }

    def __init__(self, workspace_path: str, config_path: str):
        self.workspace_path = Path(workspace_path)
        self.config_path = Path(config_path)
        self.store = VectorStore()
        self.embeddings_provider = get_embeddings_provider(use_ollama=True)
        self.chunker = ASTCodeChunker()

    def ingest(self) -> int:
        """Run the full ingestion pipeline.

        Returns:
            Number of documents indexed.
        """
        logger.info(f"Starting AST-aware ingestion for {self.workspace_path}")
        docs: list[Document] = []

        # 1. Ingest flag definitions from config
        flag_docs = self._ingest_flags()
        docs.extend(flag_docs)

        # 2. Ingest source code using AST-aware chunking
        code_docs = self._ingest_code_ast()
        docs.extend(code_docs)

        if not docs:
            logger.warning("No documents found to ingest")
            return 0

        # 3. Compute embeddings
        logger.info(f"Computing embeddings for {len(docs)} AST chunks...")
        texts = [d.text for d in docs]
        embeddings = self.embeddings_provider.embed_documents(texts)

        # 4. Store in ChromaDB
        self.store.clear()
        self.store.add_documents(docs, embeddings)

        logger.info(f"AST-aware ingestion complete. Indexed {len(docs)} chunks.")
        return len(docs)

    def _ingest_flags(self) -> list[Document]:
        """Parse flag config and create documents."""
        try:
            flags = parse_config(self.config_path)

            docs = []
            for flag in flags:
                text = (
                    f"Feature Flag Definition: {flag.name}\n"
                    f"Default Value: {flag.default_value}\n"
                    f"Description: {flag.description or 'No description'}\n"
                    f"Variations: {list(flag.variations.keys()) if flag.variations else 'Boolean'}\n"
                    f"File: {self.config_path.name}"
                )
                docs.append(Document(
                    id=f"flag:{flag.name}",
                    text=text,
                    metadata={
                        "type": "flag_definition",
                        "name": flag.name,
                        "source": str(self.config_path),
                    },
                ))
            return docs
        except Exception as e:
            logger.error(f"Failed to ingest flags: {e}")
            return []

    def _ingest_code_ast(self) -> list[Document]:
        """Scan code files and create AST-aware documents."""
        docs: list[Document] = []

        for file_path in self.workspace_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue
            if any(ex in file_path.parts for ex in self.EXCLUDE_DIRS):
                continue

            try:
                rel_path = file_path.relative_to(self.workspace_path).as_posix()
                chunks = self.chunker.chunk_file(file_path)

                for chunk in chunks:
                    # Build a rich text representation for embedding
                    header = f"File: {rel_path}"
                    if chunk.function_name:
                        header += f" | Function: {chunk.qualified_name}"
                    header += f" | Lines: {chunk.start_line}-{chunk.end_line}"
                    if chunk.flags_referenced:
                        header += f" | Flags: {', '.join(chunk.flags_referenced)}"

                    full_text = f"{header}\n\n{chunk.text}"

                    docs.append(Document(
                        id=chunk.doc_id,
                        text=full_text,
                        metadata={
                            "type": "code_chunk",
                            "chunk_type": chunk.chunk_type,
                            "file": rel_path,
                            "function_name": chunk.function_name or "",
                            "class_name": chunk.class_name or "",
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "flags_referenced": ",".join(chunk.flags_referenced),
                            "qualified_name": chunk.qualified_name,
                        },
                    ))
            except Exception as e:
                logger.warning(f"Failed to chunk {file_path}: {e}")

        logger.info(f"AST chunker produced {len(docs)} code chunks")
        return docs
