from dataclasses import dataclass
from typing import List

from BackEnd.DataObjects.Enums import EntityOrNERType


@dataclass
class Entity:
    key: str
    en_name: str
    heb_name: str
    alias: List[str]       # holds keys of other entities
    appearances: List[str]
    entityType: EntityOrNERType

    # EPerson = own class
    # EPlace =
    # ETribe =
    # ENation =
    # EPassageType =
    # ESymbol = own class
    # EMitzvah =