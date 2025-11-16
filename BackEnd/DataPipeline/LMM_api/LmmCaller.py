# bs"d
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict

from BackEnd.DataPipeline.LMM_api.LmmResponses.AnalyzedSourceResponse import AnalyzedSourceResponse
from BackEnd.DataPipeline.LMM_api.LmmResponses.RawLmmResponse import RawLmmResponse

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

    def __init__(self, api_key: Optional[str] = None):
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return
        self.api_key = api_key
        self._initialized = True
        logger.info(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def call(self, prompt: str, **kwargs) -> RawLmmResponse:
        """Make a call to the LMM API."""
        # todo
        pass

    @abstractmethod
    def analyze_src(self, src_en_content: str) -> AnalyzedSourceResponse:
        # dont forget to ask for: summary_en, summary_heb, and PassageType
        # todo
        pass

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)."""
        class_name = cls.__name__
        if class_name in cls._instances:
            del cls._instances[class_name]
            logger.info(f"{class_name} instance reset")