from dataclasses import dataclass, field
from typing import List, Optional

from BackEnd.DataObjects.Enums import EntityType


@dataclass
class Entity:
    key: str
    en_name: str
    heb_name: str
    appearances: List[str] # source types
    entityType: EntityType
    # optional:
    alias: List[str] = field(default_factory=list)  # holds keys of other entities
    book_src: Optional[str] = None                 # to differ btw Tamar in bereishit and Tamar in Shmuel B
