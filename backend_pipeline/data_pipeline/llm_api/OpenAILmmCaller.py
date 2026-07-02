# # bs"d
# """
# OpenAILmmCaller - Convenience class for OpenAI GPT-4o mini.
#
# For new code, prefer using ModelConfig and PydanticCaller directly:
#
#     from backend.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
#     from backend.data_pipeline.llm_api.PydanticCaller import PydanticCaller
#
#     ModelConfig.set_provider(ModelProvider.OPENAI)
#     caller = PydanticCaller()
# """
#
# import logging
# from backend.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
# from backend.data_pipeline.llm_api.LmmCaller import LmmCaller
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
#
# class OpenAILmmCaller(LmmCaller):
#     """
#     Convenience class that sets provider to OpenAI GPT-4o mini.
#
#     For new code, prefer using ModelConfig.set_provider(ModelProvider.OPENAI) + PydanticCaller.
#     """
#
#     def __new__(cls):
#         # Ensure OpenAI is selected when this class is used
#         ModelConfig.set_provider(ModelProvider.OPENAI)
#         logger.info("OpenAILmmCaller: Setting provider to OPENAI (GPT-4o mini)")
#         return super().__new__(cls)
#
