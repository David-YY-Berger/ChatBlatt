# bs"d - lehagdil torah velahadir

from typing import ClassVar, List
from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import EntityType


class ETribeOfIsrael(Entity):
    # Ordered tuple of transient field names used for UI display.
    TRANSIENT_DISPLAY_FIELDS: ClassVar[tuple] = (
        "membersOfTribeIsrael",
        "comparedTo",
        "contrastedWith",
    )

    entityType: EntityType = EntityType.ETribeOfIsrael

    # transient fields - TribeOfIsrael → Person/Group
    membersOfTribeIsrael: List[str] = TransientField(default_factory=list)


# DEFINED [13 tribes of Israel]