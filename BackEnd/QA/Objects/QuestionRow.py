import csv
from dataclasses import dataclass, field
from typing import List, Optional

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
    Filter_People: field(default_factory=list)
    Filter_Places: field(default_factory=list)

    def to_question_from_user(self, src_type:str) -> QuestionFromUser:
        return QuestionFromUser(src_type=src_type, question_content=self.Question_content, filters=[self.Filter_People, self.Filter_Places])