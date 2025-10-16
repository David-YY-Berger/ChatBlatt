from dataclasses import dataclass, field
from typing import Any, List

from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import SourceType
from BackEnd.DataObjects.Rel import Rel
from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass


@dataclass
class SourceMetadata (SourceClass):
    entities:List[Entity]
    rels:List[Rel]
    summary:List[str]
    sourceType: SourceType
