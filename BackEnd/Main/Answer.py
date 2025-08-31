from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from BackEnd.General import SystemFunctions
from BackEnd.DataObjects.SourceClasses import Source


@dataclass
class Answer:
    question: str
    filters: List[List[int]] # must be set by input
    refs: List[str] # must be set by input
    key: str = field(default="0")  # TODO: assign proper unique db key later
    ts: str = field(default_factory=lambda: SystemFunctions.get_ts())
    srcs: List[Source] = field(default_factory=list) #optional..


