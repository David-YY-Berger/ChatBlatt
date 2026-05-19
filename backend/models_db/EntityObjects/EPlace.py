# bs"d - lehagdil torah velahadir
from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import PlaceType, EntityType
from typing import ClassVar, List, Optional


class EPlace(Entity):
    # Ordered tuple of transient field names used for UI display.
    TRANSIENT_DISPLAY_FIELDS: ClassVar[tuple] = (
        "personsBornIn",
        "personsDiedIn",
        "personsVisited",
        "personsPrayedAt",
        "personsAssociated",
        "symbolsAssociated",
        "inNation",
        "comparedTo",
        "contrastedWith",
    )

    # db fields
    entityType: EntityType = EntityType.EPlace
    placeType: Optional[PlaceType] = None

    # transient fields
    personsDiedIn: List[str] = TransientField(default_factory=list)
    personsBornIn: List[str] = TransientField(default_factory=list)
    personsVisited: List[str] = TransientField(default_factory=list)
    personsPrayedAt: List[str] = TransientField(default_factory=list)
    personsAssociated: List[str] = TransientField(default_factory=list)  # reverse of associatedWithPlace
    symbolsAssociated: List[str] = TransientField(default_factory=list)  # reverse of Symbol→Place
    inNation: List[str] = TransientField(default_factory=list)
