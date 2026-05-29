from abc import ABC, abstractmethod
from typing import Any, List, Optional
from src.core.models.dto import HOSession, HOMessage, HOChunk

class BaseProvider(ABC):
    """
    Abstract base class for all LLM API providers (Gemini, OpenAI, etc.).
    Defines the standard interface for generating responses and handling streams.
    """
    
    @abstractmethod
    def __init__(self, api_key: str, **kwargs):
        pass

    @abstractmethod
    async def generate_response(self, session: HOSession, messages: List[HOMessage], **kwargs) -> Any:
        """
        Generates a complete response (non-streaming).
        """
        pass

    @abstractmethod
    async def stream_response(self, session: HOSession, messages: List[HOMessage], **kwargs):
        """
        Generates a streaming response, yielding HOChunk objects.
        """
        pass
