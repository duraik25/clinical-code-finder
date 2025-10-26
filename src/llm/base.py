import logging
from abc import ABC, abstractmethod
import os

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    def get_llm(self):
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama2", temperature: float = 0):
        self.model = model
        self.temperature = temperature
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def get_llm(self):
        from langchain_community.llms import Ollama
        return Ollama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url
        )


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4", temperature: float = 0):
        self.model = model
        self.temperature = temperature

    def get_llm(self):
        # Lazy import to avoid validation errors
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(f"OPENAI_API_KEY not found. Available env vars: {list(os.environ.keys())}")

        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )


def get_llm_provider() -> LLMProvider:
    """Factory function - only loads what's needed"""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        return OllamaProvider(
            model=os.getenv("OLLAMA_MODEL", "llama2"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0"))
        )
    elif provider == "openai":
        return OpenAIProvider(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0"))
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
