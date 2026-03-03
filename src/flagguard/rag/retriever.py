"""RAG Retriever module."""

from typing import List, Dict, Any
from flagguard.core.logging import get_logger
from flagguard.rag.store import VectorStore, Document
from flagguard.rag.embeddings import get_embeddings_provider

logger = get_logger("rag.retriever")


class CheckRetriever:
    """Retrieves context for a query."""
    
    def __init__(self):
        self.store = VectorStore()
        self.embeddings_provider = get_embeddings_provider(use_ollama=True)
        
    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """Retrieve most relevant documents for a query.
        
        Args:
            query: User question
            top_k: Number of docs to retrieve
            
        Returns:
            List of relevant documents
        """
        if self.store.count() == 0:
            logger.warning("Vector store is empty. Please index the codebase first.")
            return []
            
        query_embedding = self.embeddings_provider.embed_query(query)
        if not query_embedding:
            return []
            
        return self.store.query(query_embedding, n_results=top_k)
