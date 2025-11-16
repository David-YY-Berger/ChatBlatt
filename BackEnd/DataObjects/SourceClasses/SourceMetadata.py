# bs"d

from dataclasses import dataclass, field
from typing import List, Optional, Set

from BackEnd.DataObjects.Enums import SourceType, PassageType
from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass

@dataclass
class SourceMetadata(SourceClass):
    key: str
    source_type: SourceType
    summary_en: Optional[str] = None
    summary_heb: Optional[str] = None
    passage_types: List[PassageType] = field(default_factory=list)
    entities: Set[str] = field(default_factory=list)
    rels: Set[str] = field(default_factory=list)

    def __post_init__(self):
        if self.passage_types is None:
            self.passage_types = []
        if self.entities is None:
            self.entities = set()
        if self.rels is None:
            self.rels = set()

        # Optional validation example
        if not isinstance(self.key, str):
            raise ValueError("book_name must be a string")
        if not isinstance(self.source_type, SourceType):
            raise ValueError("source_type must be a SourceType instance")