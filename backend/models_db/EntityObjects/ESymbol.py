# bs"d - lehagdil torah velahadir
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import SymbolType, EntityType
from typing import Optional


class ESymbol(Entity):
    entityType: EntityType = EntityType.ESymbol
    symbolType: Optional[SymbolType] = None

