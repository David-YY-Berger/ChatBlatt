from dataclasses import dataclass
from typing import List

from BackEnd.DataObjects.Enums import EntityType


@dataclass
class Entity:
    key: str
    en_name: str
    heb_name: str
    alias: List[str]       # holds keys of other entities
    appearances: List[str] # source types
    entityType: EntityType
