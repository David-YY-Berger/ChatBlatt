from BackEnd.DataObjects.EntityObjects.Entity import Entity, TransientField
from BackEnd.DataObjects.Enums import PlaceType, EntityType
from typing import List


class EPlace(Entity):
    # db fields
    entityType: EntityType = EntityType.EPlace
    placeType: PlaceType

    # transient fields
    personsDiedIn: List[str] = TransientField(default_factory=list)
    personsBornIn: List[str] = TransientField(default_factory=list)
    personsVisited: List[str] = TransientField(default_factory=list)
    inNation: List[str] = TransientField(default_factory=list)
