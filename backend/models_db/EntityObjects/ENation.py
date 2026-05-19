# bs"d - lehagdil torah velahadir
from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import EntityType
from typing import ClassVar, List


class ENation(Entity):
    # Ordered tuple of transient field names used for UI display.
    TRANSIENT_DISPLAY_FIELDS: ClassVar[tuple] = (
        "personsBelongTo",
        "placesIn",
        "enemyOf",
        "allyOf",
        "comparedTo",
        "contrastedWith",
    )

    # db fields
    entityType: EntityType = EntityType.ENation

    # transient fields
    personsBelongTo: List[str] = TransientField(default_factory=list)
    placesIn: List[str] = TransientField(default_factory=list)
    enemyOf: List[str] = TransientField(default_factory=list)
    allyOf: List[str] = TransientField(default_factory=list)
