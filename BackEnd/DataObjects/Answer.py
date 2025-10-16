from dataclasses import dataclass, field
from typing import List

from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Rel import Rel
from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.General import SystemFunctions
from BackEnd.DataObjects.SourceClasses import SourceContent


@dataclass
class Answer:
    question_content: str
    src_metadata_lst: List[SourceMetadata] # must be set by input
    entities: List[Entity] = field(default_factory=list)
    rels: List[Rel] = field(default_factory=list)
    key: str = field(default="0")  # TODO: assign proper unique db key later
    ts: str = field(default_factory=lambda: SystemFunctions.get_ts())
    src_contents: List[SourceContent] = field(default_factory=list) #optional..


