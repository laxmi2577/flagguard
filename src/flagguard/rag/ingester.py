"""Codebase ingester for RAG."""

import os
from pathlib import Path
from typing import List, Dict, Any

from flagguard.core.logging import get_logger
from flagguard.parsers.factory import parse_config
from flagguard.rag.store import Document, VectorStore
from flagguard.rag.embeddings import get_embeddings_provider

logger = get_logger("rag.ingester")


class CodebaseIngester:
    """Ingests codebase and flags into the vector store."""
    
    def __init__(self, workspace_path: str, config_path: str):
        self.workspace_path = Path(workspace_path)
        self.config_path = Path(config_path)
        self.store = VectorStore()
        self.embeddings_provider = get_embeddings_provider(use_ollama=True)
        
    def ingest(self) -> int:
        """Run the ingestion process.
        
        Returns:
            Number of documents indexed.
        """
        logger.info(f"Starting ingestion for {self.workspace_path}")
        docs = []
        
        # 1. Ingest Flag Definitions
        flag_docs = self._ingest_flags()
        docs.extend(flag_docs)
        
        # 2. Ingest Code Usage (Basic text search for now, can enhance with AST later)
        code_docs = self._ingest_code()
        docs.extend(code_docs)
        
        if not docs:
            logger.warning("No documents found to ingest")
            return 0
            
        # 3. Compute Embeddings
        logger.info(f"Computing embeddings for {len(docs)} documents...")
        texts = [d.text for d in docs]
        embeddings = self.embeddings_provider.embed_documents(texts)
        
        # 4. Store
        self.store.clear()
        self.store.add_documents(docs, embeddings)
        
        logger.info(f"Ingestion complete. Indexed {len(docs)} documents.")
        return len(docs)
        
    def _ingest_flags(self) -> List[Document]:
        """Parse flag config and create documents."""
        try:
            flags = parse_config(self.config_path)
            
            docs = []
            for flag in flags:
                # Create a descriptive text representation for the LLM
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
                        "source": str(self.config_path)
                    }
                ))
            return docs
        except Exception as e:
            logger.error(f"Failed to ingest flags: {e}")
            return []
            
    def _ingest_code(self) -> List[Document]:
        """Scan code files for relevant context."""
        # This is a simplified scanner to find potentially relevant code
        # In a real implementation, we'd use tree-sitter or regex for flag usage
        docs = []
        
        extensions = {".py", ".js", ".ts", ".tsx", ".jsx"}
        
        for file_path in self.workspace_path.rglob("*"):
            if file_path.suffix not in extensions:
                continue
            if "node_modules" in file_path.parts or ".venv" in file_path.parts or ".git" in file_path.parts:
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Naive chunking: split by paragraphs or functions
                # For now, just chunk by lines to keep it simple and runnable
                lines = content.splitlines()
                chunk_size = 50
                overlap = 10
                
                for i in range(0, len(lines), chunk_size - overlap):
                    chunk_lines = lines[i:i + chunk_size]
                    if not chunk_lines:
                        continue
                        
                    chunk_text = "\n".join(chunk_lines)
                    start_line = i + 1
                    end_line = i + len(chunk_lines)
                    
                    # Only index chunks that look interesting (mention flags, 'feature', etc)
                    # This filters out a lot of noise
                    if any(kw in chunk_text.lower() for kw in ["flag", "feature", "config", "enable", "disable"]):
                         # Use relative path for ID to avoid collisions with same-named files in different dirs
                         rel_path = file_path.relative_to(self.workspace_path).as_posix()
                         docs.append(Document(
                            id=f"code:{rel_path}:{start_line}",
                            text=f"File: {rel_path}\nLines: {start_line}-{end_line}\n\n{chunk_text}",
                            metadata={
                                "type": "code_snippet",
                                "file": rel_path,
                                "start_line": start_line,
                                "end_line": end_line
                            }
                        ))
            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {e}")
                
        return docs
