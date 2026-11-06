# bs"d - lehagdil torah velahadir

from dataclasses import dataclass, field
from typing import List

from backend.models_db.Enums import PassageType, SourceType


@dataclass
class SourceSearchQuery:
    free_text_similarity: str
    max_sources: int
    src_types: List[SourceType] = field(default_factory=list)
    passage_types: List[PassageType] = field(default_factory=list)
    book_names: List[str] = field(default_factory=list)  # Book.database_name values
    entity_ids: List[str] = field(default_factory=list)
    rel_ids: List[str] = field(default_factory=list)
    offset: int = 0
