"""LLM integration module for generating explanations.

Uses Ollama with local models (default: Gemma 2B) to generate
human-readable explanations of conflicts and analysis results.
"""

from flagguard.llm.ollama_client import OllamaClient, LLMConfig
from flagguard.llm.explainer import ExplanationEngine

__all__ = [
    "OllamaClient",
    "LLMConfig",
    "ExplanationEngine",
]
