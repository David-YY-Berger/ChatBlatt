from typing import List
from BackEnd.DataObjects.Enums import RelType

# Relationship
class Rel:
    key:str
    term1: str # key of Entity
    term2: str # key of Entity
    appearances: List[str]
    RelType: RelType