import csv
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Question:
    BT: Optional[int]
    JT: Optional[int]
    RM: Optional[int]
    TN: Optional[int]
    MS: Optional[int]
    Question_name: Optional[str]
    Question_content: Optional[str]
    Filter_People: Optional[str]
    Filter_Places: Optional[str]