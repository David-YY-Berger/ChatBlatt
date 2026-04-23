# bs"d - lehagdil torah velahadir
from backend.models.EntityObjects.Entity import Entity
from backend.models.Enums import SymbolType, EntityType


class ESymbol(Entity):
    entityType: EntityType = EntityType.ESymbol
    symbolType: SymbolType # default?

