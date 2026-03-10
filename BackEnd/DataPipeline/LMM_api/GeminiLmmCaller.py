# # bs"d
# """
# GeminiLmmCaller - DEPRECATED
#
# This module is kept for backward compatibility.
# For new code, use ModelConfig and PydanticCaller directly:
#
#     from BackEnd.DataPipeline.LMM_api.ModelConfig import ModelConfig, ModelProvider
#     from BackEnd.DataPipeline.LMM_api.PydanticCaller import PydanticCaller
#
#     ModelConfig.set_provider(ModelProvider.GEMINI)
#     caller = PydanticCaller()
# """
#
# import logging
# from BackEnd.DataPipeline.LMM_api.ModelConfig import ModelConfig, ModelProvider
# from BackEnd.DataPipeline.LMM_api.LmmCaller import LmmCaller
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
#
# class GeminiLmmCaller(LmmCaller):
#     """
#     DEPRECATED: Use ModelConfig.set_provider(ModelProvider.GEMINI) + PydanticCaller instead.
#
#     This class is kept for backward compatibility only.
#     """
#
#     def __new__(cls):
#         # Ensure Gemini is selected when this class is used
#         ModelConfig.set_provider(ModelProvider.GEMINI)
#         logger.info("GeminiLmmCaller: Setting provider to GEMINI")
#         return super().__new__(cls)
#
