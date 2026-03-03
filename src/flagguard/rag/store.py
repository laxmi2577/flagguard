"""Vector store implementation using ChromaDB."""

import os
import shutil
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings
from flagguard.core.logging import get_logger

logger = get_logger("rag.store")


@dataclass
class Document:
    """Document to be stored in vector DB."""
    id: str
    text: str
    metadata: Dict[str, Any]


class VectorStore:
    """ChromaDB wrapper for storing and retrieving documents."""
    
    def __init__(self, persist_directory: str = ".flagguard/chroma_db"):
        self.persist_directory = persist_directory
        self._collection = None
        self._client = None
        
        self._initialize()
        
    def _initialize(self):
        """Initialize ChromaDB client."""
        try:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(name="flagguard_codebase")
            logger.info(f"Vector store initialized at {self.persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            
    def add_documents(self, documents: List[Document], embeddings: List[List[float]]):
        """Add documents with pre-computed embeddings."""
        if not self._collection or not documents:
            return
            
        ids = [doc.id for doc in documents]
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        try:
            self._collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            
    def query(self, query_embedding: List[float], n_results: int = 5) -> List[Document]:
        """Query similar documents using embedding."""
        if not self._collection:
            return []
            
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            documents = []
            if not results["ids"]:
                return []
                
            # Unpack results structure from ChromaDB
            ids = results["ids"][0]
            texts = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
            
            for i, doc_id in enumerate(ids):
                documents.append(Document(
                    id=doc_id,
                    text=texts[i],
                    metadata=metadatas[i]
                ))
                
            return documents
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
            
    def clear(self):
        """Clear all documents."""
        try:
            self._client.delete_collection("flagguard_codebase")
            self._collection = self._client.get_or_create_collection(name="flagguard_codebase")
            logger.info("Vector store cleared")
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            
    def count(self) -> int:
        """Count documents in store."""
        if not self._collection:
            return 0
        return self._collection.count()
