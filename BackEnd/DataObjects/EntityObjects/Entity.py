from pydantic import BaseModel
from typing import List, Optional

from BackEnd.DataObjects.Enums import EntityType



class Entity(BaseModel):
    key: str
    display_en_name: str
    display_heb_name: str
    all_names: List[str]
    entityType: EntityType
    # optional:
    # alias_keys: List[str] = list()  # holds keys of other entities.. take from the Rel
    book_src: Optional[str] = None                 # to differ btw Tamar in bereishit and Tamar in Shmuel B
    passage_count: Optional[int] = None
