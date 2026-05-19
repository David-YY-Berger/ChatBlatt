# bs"d - lehagdil torah velahadir
from dataclasses import dataclass, field
from typing import List, Optional
from backend.app.SourceSearchQuery import SourceSearchQuery
from backend.models_db.Enums import SourceType


@dataclass
class QuestionRow:
    BT: Optional[int]
    JT: Optional[int]
    RM: Optional[int]
    TN: Optional[int]
    MS: Optional[int]
    question_name: Optional[str]
    question_content: Optional[str]
    max_sources: Optional[int]
    entities: List = field(default_factory=list)
    rels: List = field(default_factory=list)

    def to_question_from_user(self, src_type: SourceType) -> SourceSearchQuery:

        return SourceSearchQuery(
            src_types=[src_type],
            free_text_similarity=self.question_content or "",
            entity_ids=[str(e) for e in self.entities],  # ensure strings
            rel_ids=[str(n) for n in self.rels],  # ensure strings
            max_sources=self.max_sources or 0
        )

