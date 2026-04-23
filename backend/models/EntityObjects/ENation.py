# bs"d - lehagdil torah velahadir
from backend.models.EntityObjects.Entity import Entity, TransientField
from backend.models.Enums import EntityType
from typing import List


class ENation(Entity):
    # db fields
    entityType: EntityType = EntityType.ENation

    # transient fields
    personsBelongTo: List[str] = TransientField(default_factory=list)
    placesIn: List[str] = TransientField(default_factory=list)
    enemyOf: List[str] = TransientField(default_factory=list)
    allyOf: List[str] = TransientField(default_factory=list)
