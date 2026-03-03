"""RAG Engine for Chat with Flags."""

from flagguard.core.logging import get_logger
from flagguard.rag.retriever import CheckRetriever
from flagguard.llm.ollama_client import OllamaClient
from flagguard.llm.prompts import RAG_QA_PROMPT

logger = get_logger("rag.engine")


class ChatEngine:
    """Orchestrates RAG chat flow."""
    
    def __init__(self):
        self.retriever = CheckRetriever()
        self.llm_client = OllamaClient()
        
    def chat(self, query: str, history: list = None) -> str:
        """Process a user query and return an answer.
        
        Args:
            query: User's question
            history: Chat history (not used yet, but good for future)
            
        Returns:
            LLM answer based on retrieved context
        """
        # 1. Retrieve Context
        logger.info(f"Retrieving context for: {query}")
        documents = self.retriever.retrieve(query)
        
        if not documents:
            return "I couldn't find any relevant code or flags in the project to answer your question."
            
        # 2. Format Context
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source") or doc.metadata.get("file") or "unknown"
            context_parts.append(f"[source: {source}]\n{doc.text}")
            
        context_str = "\n\n".join(context_parts)
        
        # 3. Construct Prompt
        prompt = RAG_QA_PROMPT.format(
            context=context_str,
            question=query
        )
        
        # 4. Generate Answer
        if not self.llm_client.is_available:
            return (
                "LLM is not available. Here is the relevant context I found:\n\n" + 
                "\n---\n".join([d.text[:200] + "..." for d in documents])
            )
            
        return self.llm_client.generate(prompt)
