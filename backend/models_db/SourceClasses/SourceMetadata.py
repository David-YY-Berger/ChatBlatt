# bs"d

from dataclasses import dataclass, field
from typing import List, Optional, Set

from backend.models_db.Enums import SourceType, PassageType
from backend.models_db.SourceClasses.SourceClass import SourceClass

@dataclass
class SourceMetadata(SourceClass):
    source_type: SourceType = field(init=False)
    summary_en: Optional[str] = None
    summary_heb: Optional[str] = None
    passage_types: List[PassageType] = field(default_factory=list)
    entity_keys: Set[str] = field(default_factory=set)
    rel_keys: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.passage_types is None:
            self.passage_types = []
        if self.entity_keys is None:
            self.entity_keys = set()
        if self.rel_keys is None:
            self.rel_keys = set()

        if not isinstance(self.key, str):
            raise ValueError("key must be a string")

        derived = self.get_src_type()  # uses SourceClass.get_src_type_from_key(self.key)
        if derived is None:
            raise ValueError(f"Cannot derive SourceType from key: {self.key!r}")

        self.source_type = derived
