from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from BackEnd.Sources.SourceClasses import Source


@dataclass
class Answer:
    question: str
    key: str = field(default="0")  # TODO: assign proper unique db key later
    ts: str = field(default_factory=lambda: datetime.now().isoformat())
    refs: List[str] = field(default_factory=list)
    srcs: List[Source] = field(default_factory=list)
    filters: List[List[int]] = field(default_factory=list)
