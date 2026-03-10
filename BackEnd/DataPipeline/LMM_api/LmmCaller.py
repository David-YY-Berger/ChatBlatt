# # bs"d
# """
# LmmCaller - Simple facade for LLM calls.
#
# DEPRECATED: For new code, use PydanticCaller directly with ModelConfig.
#
# Usage:
#     from BackEnd.DataPipeline.LMM_api.ModelConfig import ModelConfig, ModelProvider
#     from BackEnd.DataPipeline.LMM_api.PydanticCaller import PydanticCaller
#
#     # Set provider (default is Gemini)
#     ModelConfig.set_provider(ModelProvider.OPENAI)  # or ModelProvider.GEMINI
#
#     # Create caller
#     caller = PydanticCaller()
#     result = await caller.extract_graph_from_passage(passage)
# """
#
# import logging
# from BackEnd.DataPipeline.LMM_api.ModelConfig import ModelConfig
# from BackEnd.DataPipeline.LMM_api.PydanticCaller import PydanticCaller
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
#
# class LmmCaller:
#     """
#     Simple wrapper for LLM calls. Uses ModelConfig for provider selection.
#
#     For new code, prefer using PydanticCaller directly.
#     """
#
#     _instance = None
#
#     def __new__(cls):
#         if cls._instance is None:
#             logger.info("Creating LmmCaller instance")
#             cls._instance = super().__new__(cls)
#         return cls._instance
#
#     def __init__(self):
#         if hasattr(self, '_initialized'):
#             return
#         self.pydantic_caller = PydanticCaller()
#         self._initialized = True
#         logger.info(f"LmmCaller initialized with model: {ModelConfig.get_pydantic_model()}")
#
#     async def get_pydantic_graph_from_passage(self, clean_en_passage: str):
#         """Extract entity/relationship graph from passage."""
#         return await self.pydantic_caller.extract_graph_from_passage(clean_en_passage)
#
#     @classmethod
#     def reset_instance(cls):
#         """Reset singleton instance (useful for testing or switching providers)."""
#         cls._instance = None
#         logger.info("LmmCaller instance reset")
