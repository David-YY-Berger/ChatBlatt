from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import SymbolType, EntityType


class ESymbol(Entity):
    entityType = EntityType.ESymbol
    symbolType: SymbolType