# bs"d - lehagdil torah velahadir
from backend.models.Enums import EntityType
from backend.models.EntityObjects.Entity import Entity


class EFood(Entity):
    """
        NOT: Cow stomach in an offering (not acting as food), generic descriptions.
        Note: If something is both Food and Plant/Animal (e.g., Apple, Quail), include in both.
        Examples: Bread, Manna, Wine, Grape, Apple, Quail.
        Use the most normalized (singular), specific form.
        Represents a Food entity - edible items that act as food in the context of the passage.
        """

    # db fields
    entityType: EntityType = EntityType.EFood

    # No relationships for Food entities





