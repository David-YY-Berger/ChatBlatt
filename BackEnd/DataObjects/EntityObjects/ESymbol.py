# bs"d - lehagdil torah velahadir
from BackEnd.DataObjects.EntityObjects.Entity import Entity, TransientField
from BackEnd.DataObjects.Enums import SymbolType, EntityType
from typing import List


class ESymbol(Entity):
    entityType: EntityType = EntityType.ESymbol
    symbolType: SymbolType # default?

    # transient fields - Symbol → Place
    associatedWithPlace: List[str] = TransientField(default_factory=list)
