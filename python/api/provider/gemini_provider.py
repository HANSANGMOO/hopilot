from .base_provider import BaseProvider
from src.core.models.dto import HOSession, HOMessage
from typing import Any, List

class GeminiProvider(BaseProvider):
    """
    Provider implementation for Google Gemini API.
    """
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        # Initialize Gemini SDK or HTTP client here

    async def generate_response(self, session: HOSession, messages: List[HOMessage], **kwargs) -> Any:
        # TODO: Implement Gemini REST/SDK call
        pass

    async def stream_response(self, session: HOSession, messages: List[HOMessage], **kwargs):
        # TODO: Implement Gemini streaming logic yielding HOChunk
        pass
