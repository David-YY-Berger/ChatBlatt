from dataclasses import dataclass, field
from typing import List


@dataclass
class QuestionFromUser:
    question_content:str
    src_type:str
    filters: List[List[int]] = field(default_factory=list)