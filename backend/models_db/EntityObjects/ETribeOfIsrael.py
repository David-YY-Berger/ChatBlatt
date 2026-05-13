# bs"d - lehagdil torah velahadir

from typing import List
from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import EntityType


class ETribeOfIsrael(Entity):
    entityType: EntityType = EntityType.ETribeOfIsrael

    # transient fields - TribeOfIsrael → Person/Group
    membersOfTribeIsrael: List[str] = TransientField(default_factory=list)


# DEFINED [13 tribes of Israel]