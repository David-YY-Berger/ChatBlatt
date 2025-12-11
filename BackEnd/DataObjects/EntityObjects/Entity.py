from dataclasses import dataclass, field
from typing import List, Optional

from BackEnd.DataObjects.Enums import EntityType


@dataclass
class Entity:
    key: str
    display_en_name: str
    display_heb_name: str
    en_names: List[str]
    heb_names: List[str]
    appearances: List[str] # source types
    entityType: EntityType
    # optional:
    alias: List[str] = field(default_factory=list)  # holds keys of other entities.. take from the Rel
    book_src: Optional[str] = None                 # to differ btw Tamar in bereishit and Tamar in Shmuel B
