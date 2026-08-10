# bs"d - lehagdil torah velahadir
from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import SymbolType, EntityType
from typing import ClassVar, List, Optional


class ESymbol(Entity):
    # Ordered tuple of transient field names used for UI display.
    TRANSIENT_DISPLAY_FIELDS: ClassVar[tuple] = (
        "associatedWithPlace",
        "comparedTo",
        "contrastedWith",
    )

    entityType: EntityType = EntityType.ESymbol
    symbolType: Optional[SymbolType] = None

    def has_metadata(self) -> bool:
        return super().has_metadata() and self.symbolType is not None

    # transient fields
    associatedWithPlace: List[str] = TransientField(default_factory=list)
