# bs"d
"""
LMM API Package - Simple interface for LLM calls using Gemini or OpenAI.

Quick Start:
    from backend.data_pipeline.llm_api import ModelConfig, ModelProvider, PydanticCaller

    # Use Gemini (default)
    caller = PydanticCaller()

    # Switch to OpenAI
    ModelConfig.set_provider(ModelProvider.OPENAI)
    caller = PydanticCaller()

    # Extract data
    json_str, usage, cost = await caller.extract_graph_from_passage(passage)
"""

from backend.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
from backend.data_pipeline.llm_api.PydanticCaller import PydanticCaller

__all__ = ['ModelConfig', 'ModelProvider', 'PydanticCaller']

