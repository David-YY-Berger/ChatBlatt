# bs"d - lehagdil torah velahadir

from typing import List

from pydantic import BaseModel, Field


class EntitySelectOption(BaseModel):
    key: str = ""
    display_en_name: str
    display_heb_name: str = ""
    all_en_names: List[str] = Field(default_factory=list)
    all_heb_names: List[str] = Field(default_factory=list)





