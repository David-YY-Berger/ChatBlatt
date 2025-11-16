# bs"d

from dataclasses import dataclass, field
from typing import List, Optional

from BackEnd.DataObjects.Enums import SourceType, PassageType
from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass

@dataclass
class SourceMetadata(SourceClass):
    book_name: str
    source_type: SourceType
    summary_en: Optional[str] = None
    summary_heb: Optional[str] = None
    passage_types: List[PassageType] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    rels: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.passage_types is None:
            self.passage_types = []
        if self.entities is None:
            self.entities = []
        if self.rels is None:
            self.rels = []

        # Optional validation example
        if not isinstance(self.book_name, str):
            raise ValueError("book_name must be a string")
        if not isinstance(self.source_type, SourceType):
            raise ValueError("source_type must be a SourceType instance")