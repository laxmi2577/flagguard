"""Unit tests for RAG components."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flagguard.rag.embeddings import SentenceTransformerEmbeddings
from flagguard.rag.store import VectorStore, Document
from flagguard.rag.ingester import CodebaseIngester
from flagguard.rag.engine import ChatEngine


@pytest.fixture
def temp_chroma_db(tmp_path):
    """Create a temporary directory for ChromaDB."""
    db_path = tmp_path / "chroma_db"
    yield db_path
    if db_path.exists():
        shutil.rmtree(db_path)


def test_embedding_dimensions():
    """Test that embed_query returns a 1D list (flat)."""
    embeddings = SentenceTransformerEmbeddings()
    vector = embeddings.embed_query("test query")
    
    assert isinstance(vector, list)
    assert len(vector) > 0
    assert isinstance(vector[0], float)  # Should be float, not list
    
    # Test document embedding (should be 2D)
    docs = ["doc1", "doc2"]
    vectors = embeddings.embed_documents(docs)
    assert isinstance(vectors, list)
    assert len(vectors) == 2
    assert isinstance(vectors[0], list)
    assert isinstance(vectors[0][0], float)


def test_vector_store_operations(temp_chroma_db):
    """Test adding documents and querying the vector store."""
    store = VectorStore(persist_directory=str(temp_chroma_db))
    
    docs = [
        Document(
            id="doc1",
            text="This is a test document regarding checkout.",
            metadata={"file": "app.py", "line": 10}
        ),
        Document(
            id="doc2",
            text="This is unrelated content.",
            metadata={"file": "utils.py", "line": 5}
        )
    ]
    
    # Add documents
    embeddings = SentenceTransformerEmbeddings()
    doc_vectors = embeddings.embed_documents([d.text for d in docs])
    store.add_documents(docs, doc_vectors)
    
    assert store.count() == 2
    
    # Query
    query_vec = embeddings.embed_query("checkout")
    results = store.query(query_vec, n_results=1)
    
    assert len(results) == 1
    assert results[0].id == "doc1"
    
    # Clear
    store.clear()
    assert store.count() == 0


def test_ingestion(temp_chroma_db, sample_python_source, sample_launchdarkly_config):
    """Test ingestion of codebase and flags."""
    store = VectorStore(persist_directory=str(temp_chroma_db))
    embeddings = SentenceTransformerEmbeddings()
    
    ingester = CodebaseIngester(
        store=store,
        embeddings=embeddings,
        source_dir=sample_python_source.parent,
        config_path=sample_launchdarkly_config
    )
    
    ingester.ingest()
    
    assert store.count() > 0
    
    # Verify flag documents exist
    # (Since we can't easily query by ID without embedding, we trust count > 0 for now)
    # But let's try to query for a flag name
    query_vec = embeddings.embed_query("new_checkout")
    results = store.query(query_vec, n_results=5)
    
    # Check if we found the flag definition or usage
    found_flag = any("new_checkout" in d.text for d in results)
    assert found_flag


@patch("flagguard.rag.engine.OllamaClient")
def test_chat_engine_offline_fallback(mock_ollama_cls, temp_chroma_db):
    """Test ChatEngine fallback when LLM is offline."""
    # Setup mock LLM to be unavailable
    mock_client = MagicMock()
    mock_client.is_available = False
    mock_ollama_cls.return_value = mock_client
    
    # Setup store with some data
    store = VectorStore(persist_directory=str(temp_chroma_db))
    embeddings = SentenceTransformerEmbeddings()
    store.add_documents(
        [Document(id="1", text="Relevant context about flags.", metadata={})],
        [embeddings.embed_query("Relevant context about flags.")]
    )
    
    engine = ChatEngine(persist_directory=str(temp_chroma_db))
    
    # Override the client directly to be sure (since __init__ creates it)
    engine.llm_client = mock_client
    
    response = engine.chat("Tell me about flags")
    
    assert "LLM is not available" in response
    assert "Relevant context about flags" in response


@patch("flagguard.rag.engine.OllamaClient")
def test_chat_engine_no_docs(mock_ollama_cls, temp_chroma_db):
    """Test ChatEngine response when no documents found."""
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_ollama_cls.return_value = mock_client
    
    # Empty store
    store = VectorStore(persist_directory=str(temp_chroma_db))
    store.clear()
    
    engine = ChatEngine(persist_directory=str(temp_chroma_db))
    engine.llm_client = mock_client
    
    response = engine.chat("Unrelated query")
    
    assert "couldn't find any relevant code" in response
