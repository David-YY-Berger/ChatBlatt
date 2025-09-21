import csv
from dataclasses import dataclass, field
from typing import List, Optional

from BackEnd.DataObjects.Entity import Entity
from BackEnd.DataObjects.NER import NER
from BackEnd.Main.QuestionFromUser import QuestionFromUser


@dataclass
class QuestionRow:
    BT: Optional[int]
    JT: Optional[int]
    RM: Optional[int]
    TN: Optional[int]
    MS: Optional[int]
    Question_name: Optional[str]
    Question_content: Optional[str]
    max_sources: int
    entities: List[Entity] = field(default_factory=list)
    ners: List[NER] = field(default_factory=list)

    def to_question_from_user(self, src_type:str) -> QuestionFromUser:
        return QuestionFromUser(src_type=src_type, question_content=self.Question_content, entities=self.entities, ners=self.ners, max_sources=self.max_sources)