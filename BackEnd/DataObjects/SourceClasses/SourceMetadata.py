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
    entity_keys: Set[str] = field(default_factory=list)
    rel_keys: Set[str] = field(default_factory=list)

    def __post_init__(self):
        if self.passage_types is None:
            self.passage_types = []
        if self.entity_keys is None:
            self.entity_keys = set()
        if self.rel_keys is None:
            self.rel_keys = set()

        # Optional validation example
        if not isinstance(self.key, str):
            raise ValueError("book_name must be a string")
        if not isinstance(self.source_type, SourceType):
            raise ValueError("source_type must be a SourceType instance")