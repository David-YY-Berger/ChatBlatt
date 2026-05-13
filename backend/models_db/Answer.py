# bs"d - lehagdil torah velahadir

from dataclasses import dataclass, field
from typing import List

from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Rel import Rel
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend.common import SystemFunctions
from backend.models_db.SourceClasses import SourceContent


@dataclass
class Answer:
    question_content: str
    src_metadata_lst: List[SourceMetadata] # must be set by input
    entities: List[Entity] = field(default_factory=list)
    rels: List[Rel] = field(default_factory=list)
    key: str = field(default="0")  # TODO: assign proper unique db key later
    ts: str = field(default_factory=lambda: SystemFunctions.get_ts())
    src_contents: List[SourceContent] = field(default_factory=list) #optional..

