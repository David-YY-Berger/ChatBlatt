from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import PlaceType, EntityType


class EPlace(Entity):
    entityType: EntityType = EntityType.EPlace
    placeType: PlaceType

    # transient:
    personsDiedIn: list[str] = []
    personsBornIn: list[str] = []
    personsVisited: list[str] = []

    inNation: list[str] = []