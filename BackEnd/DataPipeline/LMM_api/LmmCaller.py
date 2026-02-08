# bs"d
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any

from BackEnd.DataPipeline.LMM_api.LmmResponses.RawLmmResponse import RawLmmResponse
from BackEnd.DataPipeline.LMM_api.PydanticCaller import PydanticCaller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LmmCaller(ABC):
    """Abstract base class for LMM API callers with lazy singleton pattern."""

    _instances: Dict[str, 'LmmCaller'] = {}

    def __new__(cls, *args, **kwargs):
        # Singleton pattern: one instance per concrete class
        class_name = cls.__name__
        if class_name not in cls._instances:
            logger.info(f"Creating new {class_name} instance (lazy initialization)")
            instance = super().__new__(cls)
            cls._instances[class_name] = instance
        else:
            logger.debug(f"Reusing existing {class_name} instance")
        return cls._instances[class_name]

    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return
        self._api_key = self._get_api_key()
        self._model_name = self._get_model_name()
        self.pydantic_caller = PydanticCaller(api_key=self._api_key, model_name=self._get_pydantic_model_name())
        self._config = self._default_config()
        self._initialized = True
        logger.info(f"{self.__class__.__name__} initialized")

    ################################################ METHODS ########################################################

    def get_pydantic_graph_from_passage(self, clean_en_passage: str):
        return self.pydantic_caller.extract_graph_from_passage(clean_en_passage)

    @abstractmethod
    def call(self, prompt: str) -> RawLmmResponse:
        """Make a call to the LMM API."""
        pass

    # def analyze_src(self, src_en_content: str) -> AnalyzedSourceResponse:
    #     # dont forget to ask for: summary_en, summary_heb, and PassageType
    #     # todo
    #     pass
    #
    # def get_entity_metadata(self, entities: List[Entity]) -> AnalyzedEntitiesResponse:
    #     pass


    ############################################### CONFIG / SETTERS   ###############################################
    @staticmethod
    def _default_config() -> Dict[str, Any]:
        return {
            'temperature': 0.0,  # deterministic, required for strict JSON
            'max_tokens': 2500,  # todo must investigate this..
            'top_p': 0.95,  # fine to keep; harmless with temp=0
            'top_k': 40,  # unused with temp=0 but doesn’t hurt
        }

    def set_temperature(self, temperature: float) -> 'LmmCaller':
        """Set the temperature parameter (0.0 to 1.0)."""
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        self._config['temperature'] = temperature
        return self

    def set_max_tokens(self, max_tokens: int) -> 'LmmCaller':
        """Set the maximum number of tokens to generate."""
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        self._config['max_tokens'] = max_tokens
        return self

    def set_top_p(self, top_p: float) -> 'LmmCaller':
        """Set the top_p (nucleus sampling) parameter."""
        if not 0.0 <= top_p <= 1.0:
            raise ValueError("top_p must be between 0.0 and 1.0")
        self._config['top_p'] = top_p
        return self

    def set_top_k(self, top_k: int) -> 'LmmCaller':
        """Set the top_k parameter."""
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        self._config['top_k'] = top_k
        return self

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def reset_config(self) -> 'LmmCaller':
        """Reset configuration to defaults."""
        self._config = self._default_config()
        return self

    @abstractmethod
    def _get_model_name(self):
        return 'must initialize in child class'

    @abstractmethod
    def _get_pydantic_model_name(self):
        return 'must initialize in child class'

    @abstractmethod
    def _get_api_key(self):
        return 'must initialize in child class'

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)."""
        class_name = cls.__name__
        if class_name in cls._instances:
            del cls._instances[class_name]
            logger.info(f"{class_name} instance reset")
