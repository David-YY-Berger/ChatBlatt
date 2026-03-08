
from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import EntityType


class ENation(Entity):
    entityType: EntityType = EntityType.ENation

    # transient:
    personsBelongTo: list[str] = []
    placesIn: list[str] = []

    enemyOf: list[str] = []
    allyOf: list[str] = []