from dataclasses import dataclass, field
from typing import List



@dataclass
class QuestionFromUser:
    question_content: str
    src_type: str
    max_sources: int
    entities: List[str] = field(default_factory=list)
    rels: List[str] = field(default_factory=list)