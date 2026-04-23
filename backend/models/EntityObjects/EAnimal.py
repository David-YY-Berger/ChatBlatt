# bs"d - lehagdil torah velahadir

from backend.models.EntityObjects.Entity import Entity, TransientField
from backend.models.Enums import EntityType
from typing import List


class EAnimal(Entity):
    """
    Represents an Animal entity - includes both real and mythical animals.
    Examples: Lion, Eagle, Serpent, Leviathan, Balaam's Donkey.
    Includes talking animals that were previously under Person.
    """
    # db fields
    entityType: EntityType = EntityType.EAnimal

    # transient fields - Animal can only participate in spokeWith relationship
    spokeWith: List[str] = TransientField(default_factory=list)



