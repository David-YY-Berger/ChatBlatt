from dataclasses import dataclass, field
from typing import List

from BackEnd.DataObjects.Entity import Entity
from BackEnd.DataObjects.NER import NER


@dataclass
class QuestionFromUser:
    question_content:str
    src_type:str
    max_sources: int
    entities: List[Entity] = field(default_factory=list)
    ners: List[NER] = field(default_factory=list)