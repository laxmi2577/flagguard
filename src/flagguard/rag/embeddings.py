"""Embeddings service for FlagGuard RAG.

Supports both SentenceTransformers (HuggingFace) and Ollama for checking.
"""

from typing import List, Protocol
from dataclasses import dataclass
from flagguard.core.logging import get_logger
from flagguard.llm.ollama_client import OllamaClient

logger = get_logger("rag.embeddings")


class EmbeddingsProvider(Protocol):
    """Protocol for embedding providers."""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        ...
        
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        ...


class SentenceTransformerEmbeddings:
    """Embeddings using sentence-transformers (HuggingFace)."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.is_available = True
        except ImportError:
            logger.warning("sentence-transformers not installed. RAG features will be limited.")
            self.is_available = False
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {e}")
            self.is_available = False
            
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.is_available:
            return []
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
        
    def embed_query(self, text: str) -> List[float]:
        if not self.is_available:
            return []
        embedding = self.model.encode(text)
        embedding_list = embedding.tolist()
        
        # Ensure it's a flat list (1D)
        if embedding_list and isinstance(embedding_list[0], list):
            return embedding_list[0]
            
        return embedding_list


class OllamaEmbeddings:
    """Embeddings using Ollama API."""
    
    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name
        self.client = OllamaClient()
        # Check if embedding model is available
        self.is_available = self.client.is_available and self._check_model()
        
    def _check_model(self) -> bool:
        """Check if embedding model exists, pull if not."""
        if not self.client.is_available:
            return False
            
        try:
            # Simple check by trying to embed
            import ollama
            ollama.embeddings(model=self.model_name, prompt="test")
            return True
        except Exception:
            logger.info(f"Embedding model {self.model_name} not found, pulling...")
            try:
                import ollama
                ollama.pull(self.model_name)
                return True
            except Exception as e:
                logger.warning(f"Failed to pull embedding model: {e}")
                return False

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.is_available:
            return []
        
        embeddings = []
        import ollama
        for text in texts:
            try:
                resp = ollama.embeddings(model=self.model_name, prompt=text)
                embeddings.append(resp["embedding"])
            except Exception as e:
                logger.error(f"Ollama embedding failed: {e}")
                embeddings.append([])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        if not self.is_available:
            return []
            
        try:
            import ollama
            resp = ollama.embeddings(model=self.model_name, prompt=text)
            return resp["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            return []


def get_embeddings_provider(use_ollama: bool = False) -> EmbeddingsProvider:
    """Factory to get embeddings provider."""
    if use_ollama:
        provider = OllamaEmbeddings()
        if provider.is_available:
            return provider
        logger.warning("Ollama embeddings unavailable, falling back to SentenceTransformer")
    
    return SentenceTransformerEmbeddings()
