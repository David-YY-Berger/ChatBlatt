from dataclasses import dataclass, field
from typing import List, Optional

from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Rel import Rel
from BackEnd.Main.QuestionFromUser import QuestionFromUser


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

    def to_question_from_user(self, src_type: str) -> QuestionFromUser:
        return QuestionFromUser(
            src_type=src_type,
            question_content=self.question_content or "",
            entities=[str(e) for e in self.entities],  # ensure strings
            rels=[str(n) for n in self.rels],  # ensure strings
            max_sources=self.max_sources or 0
        )


