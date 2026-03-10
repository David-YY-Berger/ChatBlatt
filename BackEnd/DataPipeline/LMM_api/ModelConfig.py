# bs"d
"""
Simple model configuration for switching between LLM providers.

Usage:
    from BackEnd.DataPipeline.LMM_api.ModelConfig import ModelConfig, ModelProvider

    # Switch to GPT-4o mini (paid):
    ModelConfig.set_provider(ModelProvider.OPENAI)

    # Switch to Gemini Free:
    ModelConfig.set_provider(ModelProvider.GEMINI_FREE)

    # Switch to Gemini Paid:
    ModelConfig.set_provider(ModelProvider.GEMINI_PAID)

    # Get current model string for pydantic-ai:
    model_str = ModelConfig.get_pydantic_model()
"""

import os
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ModelProvider(Enum):
    """
    Available LLM providers.

    GEMINI_FREE  - Google AI Studio free tier (rate limited, good for testing)
    GEMINI_PAID  - Google AI Studio paid tier (higher limits)
    OPENAI       - OpenAI GPT-4o-mini (always paid, no free API tier)
    """
    GEMINI_FREE = "gemini_free"
    GEMINI_PAID = "gemini_paid"
    OPENAI = "openai"


class ModelConfig:
    """
    Central configuration for LLM model selection.
    Makes it simple to switch between Gemini (free/paid) and OpenAI.

    .env file should contain:
        GEMINI_FREE_API_KEY=your_free_key_here
        GEMINI_PAID_API_KEY=your_paid_key_here
        OPENAI_API_KEY=your_openai_key_here
    """

    # Default provider - change this to switch globally
    _current_provider: ModelProvider = ModelProvider.GEMINI_FREE

    # Model names for each provider
    MODELS = {
        ModelProvider.GEMINI_FREE: "gemini-2.5-flash",
        ModelProvider.GEMINI_PAID: "gemini-2.5-flash",
        ModelProvider.OPENAI: "gpt-4o-mini",
    }

    # Environment variable names for API keys
    API_KEY_ENV_VARS = {
        ModelProvider.GEMINI_FREE: "GEMINI_FREE_API_KEY",
        ModelProvider.GEMINI_PAID: "GEMINI_PAID_API_KEY",
        ModelProvider.OPENAI: "OPENAI_API_KEY",
    }

    # pydantic-ai model string prefixes
    PYDANTIC_PREFIXES = {
        ModelProvider.GEMINI_FREE: "google-gla:",
        ModelProvider.GEMINI_PAID: "google-gla:",
        ModelProvider.OPENAI: "openai:",
    }

    # Cost per million tokens (approximate, for logging)
    COST_PER_MILLION = {
        ModelProvider.GEMINI_FREE: {"input": 0.0, "output": 0.0},        # Free!
        ModelProvider.GEMINI_PAID: {"input": 0.075, "output": 0.30},     # Gemini 2.5 Flash
        ModelProvider.OPENAI: {"input": 0.15, "output": 0.60},           # GPT-4o-mini
    }

    @classmethod
    def set_provider(cls, provider: ModelProvider) -> None:
        """Set the active LLM provider."""
        cls._current_provider = provider

    @classmethod
    def get_provider(cls) -> ModelProvider:
        """Get the current LLM provider."""
        return cls._current_provider

    @classmethod
    def get_model_name(cls) -> str:
        """Get the model name for the current provider."""
        return cls.MODELS[cls._current_provider]

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Get the API key for the current provider from environment."""
        env_var = cls.API_KEY_ENV_VARS[cls._current_provider]
        return os.getenv(env_var)

    @classmethod
    def get_pydantic_model(cls) -> str:
        """
        Get the model string for pydantic-ai.

        Returns:
            Model string like 'google-gla:gemini-2.5-flash' or 'openai:gpt-4o-mini'
        """
        prefix = cls.PYDANTIC_PREFIXES[cls._current_provider]
        model = cls.MODELS[cls._current_provider]
        return f"{prefix}{model}"

    @classmethod
    def get_cost_per_million(cls) -> dict:
        """Get the cost per million tokens for current provider."""
        return cls.COST_PER_MILLION[cls._current_provider]

    @classmethod
    def ensure_api_key_in_env(cls) -> None:
        """
        Ensure the appropriate API key environment variable is set.
        For Gemini: sets GOOGLE_API_KEY (required by pydantic-ai)
        For OpenAI: sets OPENAI_API_KEY (required by pydantic-ai)
        """
        api_key = cls.get_api_key()
        if not api_key:
            raise ValueError(
                f"API key not found. Please set {cls.API_KEY_ENV_VARS[cls._current_provider]} "
                f"in your .env file."
            )

        # pydantic-ai expects GOOGLE_API_KEY for Gemini
        if cls._current_provider in (ModelProvider.GEMINI_FREE, ModelProvider.GEMINI_PAID):
            os.environ['GOOGLE_API_KEY'] = api_key
        # pydantic-ai expects OPENAI_API_KEY for OpenAI
        elif cls._current_provider == ModelProvider.OPENAI:
            os.environ['OPENAI_API_KEY'] = api_key

