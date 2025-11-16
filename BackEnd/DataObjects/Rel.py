from dataclasses import dataclass, field
from typing import List
from BackEnd.DataObjects.Enums import RelType

# Relationship
@dataclass
class Rel:
    key: str
    term1: str # key of Entity
    term2: str # key of Entity
    rel_type: RelType
    appearances: List[str] = field(default_factory=list)
