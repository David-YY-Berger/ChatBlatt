# bs"d - lehagdil torah velahadir

"""Backward-compatible facade for split Pydantic model modules.

This file keeps the original import surface stable while implementation now lives
in smaller modules in the same directory.
"""

from backend.models.Enums import NumberCategory
from backend.models.PydanticModels.entity_models import Entities, Entity, NumberEntity
from backend.models.PydanticModels.name_utils import smart_title_case
from backend.models.PydanticModels.number_normalization import (
    _FRACTION_WORDS,
    _NUMBER_SCALES,
    _NUMBER_WORDS,
    _SPECIAL_CORRECTIONS,
    _normalize_number_string,
    _parse_word_number,
)
from backend.models.PydanticModels.pydantic_constants import (
    DEMONYM_TO_NATION,
    ENTITY_CATEGORIES,
    PERSON_PLACE_SPECIFIC_RELATIONSHIPS,
    SYMMETRIC_RELATIONSHIPS,
    TRIBES_OF_ISRAEL,
    _NUMBER_CATEGORY_VALUES,
    max_len_summary,
    min_len_summary,
)
from backend.models.PydanticModels.relationship_models import Relation, Relationships
from backend.models.PydanticModels.response_models import ExtractionResult, FinalResponse

__all__ = [
    "TRIBES_OF_ISRAEL",
    "ENTITY_CATEGORIES",
    "DEMONYM_TO_NATION",
    "SYMMETRIC_RELATIONSHIPS",
    "PERSON_PLACE_SPECIFIC_RELATIONSHIPS",
    "max_len_summary",
    "min_len_summary",
    "smart_title_case",
    "_NUMBER_WORDS",
    "_NUMBER_SCALES",
    "_FRACTION_WORDS",
    "_SPECIAL_CORRECTIONS",
    "_normalize_number_string",
    "_parse_word_number",
    "_NUMBER_CATEGORY_VALUES",
    "NumberCategory",
    "Entity",
    "NumberEntity",
    "Entities",
    "Relation",
    "Relationships",
    "ExtractionResult",
    "FinalResponse",
]

