# bs"d - lehagdil torah velahadir

from backend.models.EntityObjects.Entity import Entity
from backend.models.Enums import EntityType


class EPlant(Entity):
    """
    Represents a Plant entity - includes both edible and inedible plants.
    Use the most normalized (singular), specific form.
    Examples: Grape, Fig, Cedar, Hyssop, Apple, Wheat, Olive.
    Note: 'Grape vine', 'Grape tree', 'Grape' should all just be 'Grape'.
    Note: If something is both Plant and Food (e.g., Apple), include in both.
    """
    # db fields
    entityType: EntityType = EntityType.EPlant
    # No relationships for Plant entities

