# bs"d - lehagdil torah velahadir

from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import EntityType
from typing import ClassVar, List


class EAnimal(Entity):
    """
    Represents an Animal entity - includes both real and mythical animals.
    Examples: Lion, Eagle, Serpent, Leviathan, Balaam's Donkey.
    Includes talking animals that were previously under Person.
    """
    # Ordered tuple of transient field names used for UI display.
    TRANSIENT_DISPLAY_FIELDS: ClassVar[tuple] = (
        "spokeWith",
        "comparedTo",
        "contrastedWith",
    )

    # db fields
    entityType: EntityType = EntityType.EAnimal

    # transient fields - Animal can only participate in spokeWith relationship
    spokeWith: List[str] = TransientField(default_factory=list)



