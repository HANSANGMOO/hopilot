from typing import Dict, Optional
from src.api.provider.base_provider import BaseProvider
from src.api.provider.gemini_provider import GeminiProvider
from src.api.provider.openai_provider import OpenAIProvider

class APIManager:
    """
    Manager class responsible for initializing and routing requests to the correct LLM provider.
    """
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        
    def initialize_providers(self, env_config: dict):
        """
        Initializes providers based on available API keys in the environment config.
        """
        # Example initialization (to be expanded)
        gemini_key = env_config.get("GEMINI_API_KEY")
        if gemini_key:
            self.providers["gemini"] = GeminiProvider(api_key=gemini_key)
            
        openai_key = env_config.get("OPENAI_API_KEY")
        if openai_key:
            self.providers["openai"] = OpenAIProvider(api_key=openai_key)

    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """
        Retrieves a registered provider by name.
        """
        return self.providers.get(provider_name.lower())
