"""Ollama client for local LLM inference.

Provides a wrapper around the Ollama API for generating
explanations using local models.
"""

from dataclasses import dataclass
from typing import Any

from flagguard.core.logging import get_logger

logger = get_logger("ollama_client")


@dataclass
class LLMConfig:
    """Configuration for the LLM client.
    
    Attributes:
        model: Model name to use (e.g., "gemma2:2b")
        host: Ollama server URL
        temperature: Sampling temperature (lower = more deterministic)
        max_tokens: Maximum tokens to generate
    """
    model: str = "gemma2:2b"
    host: str = "http://localhost:11434"
    temperature: float = 0.3
    max_tokens: int = 500


class OllamaClient:
    """Client for Ollama local LLM inference.
    
    Wraps the Ollama Python library to provide a simple interface
    for generating text completions.
    
    Attributes:
        config: LLM configuration
        is_available: Whether Ollama is available
    """
    
    def __init__(self, config: LLMConfig | None = None) -> None:
        """Initialize the client.
        
        Args:
            config: Optional LLM configuration
        """
        self.config = config or LLMConfig()
        self._client: Any = None
        self.is_available = False
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize the Ollama client."""
        try:
            import ollama
            self._client = ollama.Client(host=self.config.host)
            
            # Test connection by listing models
            self._client.list()
            self.is_available = True
            logger.info(f"Ollama connected at {self.config.host}")
        except ImportError:
            logger.warning("Ollama package not installed")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
    
    def generate(self, prompt: str) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: The input prompt
            
        Returns:
            Generated text response
        """
        if not self.is_available or not self._client:
            return self._fallback_response(prompt)
        
        try:
            response = self._client.generate(
                model=self.config.model,
                prompt=prompt,
                options={
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            )
            return response.get("response", "")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when LLM is unavailable."""
        return (
            "[LLM unavailable] Unable to generate explanation. "
            "Please install Ollama and ensure it's running."
        )
    
    def check_model_available(self) -> bool:
        """Check if the configured model is available.
        
        Returns:
            True if the model is available, False otherwise
        """
        if not self.is_available or not self._client:
            return False
        
        try:
            models = self._client.list()
            model_names = [m.get("name", "") for m in models.get("models", [])]
            return any(self.config.model in name for name in model_names)
        except Exception:
            return False
    
    def pull_model(self) -> bool:
        """Pull the configured model.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available or not self._client:
            return False
        
        try:
            logger.info(f"Pulling model: {self.config.model}")
            self._client.pull(self.config.model)
            return True
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False
