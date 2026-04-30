"""
LLM Provider Abstraction Layer
Supports: Anthropic (Claude), OpenAI, Groq
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import os


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        """
        Initialize LLM provider.
        
        Args:
            api_key: API key for the provider
            model: Model name/ID
            **kwargs: Additional provider-specific options
        """
        self.api_key = api_key
        self.model = model
        self.kwargs = kwargs
    
    @abstractmethod
    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """
        Send messages to LLM and get response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Response text from LLM
        """
        pass
    
    def validate_api_key(self) -> bool:
        """Validate that API key is set."""
        return bool(self.api_key)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", **kwargs):
        """Initialize Anthropic provider."""
        super().__init__(api_key, model, **kwargs)
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package required: pip install anthropic")
    
    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """Send messages to Claude and get response."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=messages[0]['content'] if messages[0]['role'] == 'system' else None,
            messages=[m for m in messages if m['role'] != 'system'],
        )
        return response.content[0].text


def _openai_completion_params(model: str, max_tokens: int, temperature: float) -> dict:
    """
    Build the right token-limit and temperature params for a given OpenAI model.

    - Newer models (o-series, gpt-4.5, gpt-5.x) require 'max_completion_tokens'.
    - o-series models do not accept a 'temperature' parameter.
    """
    # Prefixes that require max_completion_tokens
    new_style = model.startswith(("o1", "o3", "o4", "gpt-4.5", "gpt-5"))
    # o-series models also reject temperature
    no_temperature = model.startswith(("o1", "o3", "o4"))

    params: dict = {"model": model, "messages": []}  # placeholder; caller fills messages
    if new_style:
        params["max_completion_tokens"] = max_tokens
    else:
        params["max_tokens"] = max_tokens
    if not no_temperature:
        params["temperature"] = temperature
    return params


class OpenAIProvider(LLMProvider):
    """OpenAI provider — supports legacy (gpt-4o, gpt-4.1) and new-style (gpt-5.x, o-series) models."""

    def __init__(self, api_key: str, model: str = "gpt-4o", **kwargs):
        super().__init__(api_key, model, **kwargs)
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package required: pip install openai")

    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        params = _openai_completion_params(self.model, max_tokens, temperature)
        params["messages"] = messages
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content


class GroqProvider(LLMProvider):
    """Groq provider (fast inference with Llama, Mixtral, etc.)."""
    
    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768", **kwargs):
        """Initialize Groq provider."""
        super().__init__(api_key, model, **kwargs)
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
        except ImportError:
            raise ImportError("groq package required: pip install groq")
    
    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """Send messages to Groq and get response."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        return response.choices[0].message.content


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider."""

    def __init__(self, api_key: str, model: str = "gpt-4.1", **kwargs):
        super().__init__(api_key, model, **kwargs)
        endpoint = kwargs.get("azure_endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_version = kwargs.get("api_version") or os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        if not endpoint:
            raise EnvironmentError("AZURE_OPENAI_ENDPOINT not set.")
        try:
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version,
            )
        except ImportError:
            raise ImportError("openai package required: pip install openai")
        # Azure uses the deployment name as the model identifier
        self.deployment = kwargs.get("azure_deployment") or os.environ.get("AZURE_OPENAI_DEPLOYMENT", model)

    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        params = _openai_completion_params(self.deployment, max_tokens, temperature)
        params["messages"] = messages
        params["model"] = self.deployment
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content


class GeminiProvider(LLMProvider):
    """Google Gemini provider via google-generativeai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", **kwargs):
        super().__init__(api_key, model, **kwargs)
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._genai = genai
        except ImportError:
            raise ImportError("google-generativeai package required: pip install google-generativeai")

    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        # Separate system prompt from conversation
        system_prompt = None
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                # Gemini uses 'user'/'model' roles
                role = "model" if m["role"] == "assistant" else "user"
                chat_messages.append({"role": role, "parts": [m["content"]]})

        model = self._genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt,
            generation_config=self._genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        # Single-turn: send the last user message
        response = model.generate_content(chat_messages)
        return response.text


class LLMFactory:
    """Factory for creating LLM provider instances."""

    PROVIDERS = {
        'anthropic':   AnthropicProvider,
        'claude':      AnthropicProvider,
        'openai':      OpenAIProvider,
        'azure':       AzureOpenAIProvider,
        'azure_openai': AzureOpenAIProvider,
        'groq':        GroqProvider,
        'gemini':      GeminiProvider,
        'google':      GeminiProvider,
    }

    DEFAULT_MODELS = {
        'anthropic':   'claude-sonnet-4-6',
        'claude':      'claude-sonnet-4-6',
        'openai':      'gpt-4o',
        'azure':       'gpt-4.1',
        'azure_openai': 'gpt-4.1',
        'groq':        'mixtral-8x7b-32768',
        'gemini':      'gemini-2.0-flash',
        'google':      'gemini-2.0-flash',
    }
    
    @classmethod
    def create(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider: Provider name ('anthropic', 'openai', 'groq')
            api_key: API key (defaults to environment variable)
            model: Model name (defaults to provider default)
            **kwargs: Additional provider-specific options
            
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If provider not supported
            EnvironmentError: If API key not found
            
        Example:
            >>> llm = LLMFactory.create('openai')
            >>> response = llm.create_message([{'role': 'user', 'content': 'Hello'}])
        """
        provider = provider.lower()
        
        if provider not in cls.PROVIDERS:
            supported = ', '.join(cls.PROVIDERS.keys())
            raise ValueError(f"Unknown provider: {provider}. Supported: {supported}")
        
        # Get API key from argument or environment
        if api_key is None:
            env_var = {
                'anthropic':    'ANTHROPIC_API_KEY',
                'claude':       'ANTHROPIC_API_KEY',
                'openai':       'OPENAI_API_KEY',
                'azure':        'AZURE_OPENAI_API_KEY',
                'azure_openai': 'AZURE_OPENAI_API_KEY',
                'groq':         'GROQ_API_KEY',
                'gemini':       'GEMINI_API_KEY',
                'google':       'GEMINI_API_KEY',
            }.get(provider)

            api_key = os.environ.get(env_var)
            if not api_key:
                raise EnvironmentError(
                    f"{env_var} not set. "
                    f"Set it: export {env_var}='your-key' (or set in .env)"
                )
        
        # Get model from argument or default
        if model is None:
            model = cls.DEFAULT_MODELS.get(provider)
        
        # Create and return provider instance
        provider_class = cls.PROVIDERS[provider]
        return provider_class(api_key=api_key, model=model, **kwargs)
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of supported provider names."""
        return list(cls.PROVIDERS.keys())
    
    @classmethod
    def get_default_model(cls, provider: str) -> str:
        """Get default model for a provider."""
        return cls.DEFAULT_MODELS.get(provider.lower(), 'unknown')


if __name__ == "__main__":
    print("LLM Provider Abstraction Layer")
    print("\nSupported Providers:")
    for p in LLMFactory.get_supported_providers():
        print(f"  • {p:12} (default model: {LLMFactory.get_default_model(p)})")
    
    print("\nEnvironment Variables Required:")
    print("  • ANTHROPIC_API_KEY - For Anthropic/Claude")
    print("  • OPENAI_API_KEY    - For OpenAI")
    print("  • GROQ_API_KEY      - For Groq")
    
    print("\nUsage Example:")
    print("  from utils.llm_provider import LLMFactory")
    print("  llm = LLMFactory.create('openai')")
    print("  response = llm.create_message([{'role': 'user', 'content': 'Hello'}])")
