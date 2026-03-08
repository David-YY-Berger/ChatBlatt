from pydantic import BaseModel
from typing import List, Optional

from BackEnd.DataObjects.Enums import EntityType



class Entity(BaseModel):
    # db fields
    key: str
    display_en_name: str
    display_heb_name: str
    all_en_names: List[str]
    all_heb_names: List[str]
    entityType: EntityType
    alias_keys: List[str] = list()  # holds keys of other entities..

#     transient fields
    comparedTo: list[str] = list()
    contrastedWith: list[str] = list()
