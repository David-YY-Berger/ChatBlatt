# bs"d
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List

from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataPipeline.LMM_api.LmmResponses.AnalyzedEntitiesResponse import AnalyzedEntitiesResponse
from BackEnd.DataPipeline.LMM_api.LmmResponses.AnalyzedSourceResponse import AnalyzedSourceResponse
from BackEnd.DataPipeline.LMM_api.LmmResponses.RawLmmResponse import RawLmmResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LmmCaller(ABC):
    """Abstract base class for LMM API callers with lazy singleton pattern."""

    _instances: Dict[str, 'LmmCaller'] = {}
    prompt_get_entity_rel_from_passage = """
Extract all entities and relationships from the following passage ({text_source}).

Return ONLY valid JSON in this schema:

{
  "res": {
    "Entities": {
      "Person": [ { "en_name": "" }, ... ], 
      "Place": [ { "en_name": "" }, ... ],
      "TribeOfIsrael": [ { "en_name": "" }, ... ], 
      "Nation": [ { "en_name": "" }, ... ],
      "Symbol": [ { "en_name": "" }, ... ]
    },
    "Rel": {
      "studiedFrom": [ { "term1": "", "term2": "" }, ... ], 
      "siblingWith": [ { "term1": "", "term2": "" }, ... ], 
      "childOf": [ { "term1": "", "term2": "" }, ... ], 
      "spouseOf": [ { "term1": "", "term2": "" }, ... ], 
      "descendantOf": [ { "term1": "", "term2": "" }, ... ], 
      "bornIn": [ { "term1": "", "term2": "" }, ... ], 
      "diedIn": [ { "term1": "", "term2": "" }, ... ], 
      "residedIn": [ { "term1": "", "term2": "" }, ... ], 
      "visited": [ { "term1": "", "term2": "" }, ... ], 
      "personToTribeOfIsrael": [ { "term1": "", "term2": "" }, ... ], 
      "personToNation": [ { "term1": "", "term2": "" }, ... ],
      "EnemyOf": [ { "term1": "", "term2": "" }, ... ], 
      "AllyOf": [ { "term1": "", "term2": "" }, ... ], 
      "placeToNation": [ { "term1": "", "term2": "" }, ... ], 
      "comparedTo": [ { "term1": "", "term2": "" }, ... ], 
      "contrastedWith": [ { "term1": "", "term2": "" }, ... ], 
      "alias": [ { "term1": "", "term2": "" }, ... ],
      "aliasFromSages": [ { "term1": "", "term2": "" }, ... ]
    }
  }
}

Rules:
1. All lists may contain multiple entries. If a list is empty, omit its key entirely.
2. Include only entity types and relationship types that appear in the passage.
3. Any term used in Rel (term1 or term2) must also appear in Entities with the same normalized name.
4. "en_name" must be normalized (e.g., "Edom" not "Edomite"; "Abraham" not "Abraham's").
5. "term1" and "term2" must exactly match normalized "en_name" values.
6. Output valid JSON only, with no extra text.

Relationship typing rules (strict):
- Person ↔ Person:
  studiedFrom, siblingWith, childOf, spouseOf, descendantOf
- Person → Place:
  bornIn, diedIn, residedIn, visited
- Person → TribeOfIsrael:
  personToTribeOfIsrael
- Person → Nation:
  personToNation
- Nation ↔ Nation:
  EnemyOf, AllyOf
- Place → Nation:
  placeToNation
- Any entity → Symbol:
  comparedTo, contrastedWith
- Any entity ↔ Any entity (same normalized name allowed):
  alias, aliasFromSages
- Enforce directional/typing consistency:
  term1 and term2 must match the allowed entity types above, otherwise the relationship must be omitted.
- TribeOfIsrael entities must be one of the 13 tribes; "Israel" itself should be represented as a Nation.
"""


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

    @abstractmethod
    def get_entity_metadata(self, entities: List[Entity]) -> AnalyzedEntitiesResponse:
        pass

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)."""
        class_name = cls.__name__
        if class_name in cls._instances:
            del cls._instances[class_name]
            logger.info(f"{class_name} instance reset")