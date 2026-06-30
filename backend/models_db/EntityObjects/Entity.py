# bs"d - lehagdil torah velahadir

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from backend.models_db.Enums import EntityType

if TYPE_CHECKING:
    from backend.models_db.EntityObjects.EntityIdentity import EntityIdentityContext


# Helper function for transient fields (excluded from serialization/db)
def TransientField(default=None, default_factory=None, **kwargs):
    """Mark a field as transient - will be excluded from db operations."""
    if default_factory is not None:
        return Field(default_factory=default_factory, exclude=True, **kwargs)
    return Field(default=default, exclude=True, **kwargs)


class Entity(BaseModel):
    # db fields
    key: str = ""
    display_en_name: str
    display_heb_name: str = ""
    all_en_names: List[str] = Field(default_factory=list)
    all_heb_names: List[str] = Field(default_factory=list)
    entityType: EntityType
    alias_keys: List[str] = Field(default_factory=list)

    # transient fields
    comparedTo: List[str] = TransientField(default_factory=list)
    contrastedWith: List[str] = TransientField(default_factory=list)
    # Navigation metadata: maps display_name -> (entity_key, EntityType)
    # Populated by the entity populator; used by the UI for click-through navigation.
    rel_links: Dict[str, Tuple[str, Any]] = TransientField(default_factory=dict)

    # ========================= Identity / Equality =========================

    def get_identity_tuple(self, context: Optional["EntityIdentityContext"] = None) -> tuple:
        """
        Returns a hashable tuple that uniquely identifies this entity for dedup purposes.
        Two entities with the same identity tuple are considered 'the same entity'.

        Default: (display_en_name lowercased, entityType).
        Subclasses override for richer semantics.
        """
        return (self.display_en_name.lower(), self.entityType)

    def build_existence_query(self, context: Optional["EntityIdentityContext"] = None) -> Dict[str, Any]:
        """
        Returns a MongoDB query dict to find an existing entity that is 'equal' to this one.
        Used by the DB layer for dedup on insert.

        Default: match by display_en_name (case-insensitive) + entityType.
        Subclasses override for richer semantics.
        """
        from backend.db.DBConstants import DBFields, DBOperators
        return {
            DBFields.DISPLAY_EN_NAME: {DBOperators.REGEX: f"^{self.display_en_name}$", DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE},
            DBFields.ENTITY_TYPE: self.entityType.value,
        }

    @classmethod
    def get_class_for_type(cls, entity_type: EntityType) -> "Type[Entity]":
        """
        Returns the Entity subclass whose entityType default matches the given type,
        or Entity itself if no specialized subclass has been imported yet.

        Works via Python's __subclasses__() — no explicit registry needed.
        Any subclass that has been imported is automatically discoverable.
        """
        for subclass in cls.__subclasses__():
            field = subclass.model_fields.get("entityType")
            if field is not None and field.default == entity_type:
                return subclass
        return cls

    @classmethod
    def create_from_en_name(cls, en_name: str, entity_type: EntityType) -> "Entity":
        """Factory: create an Entity from just the English display name and type."""
        return cls(
            display_en_name=en_name,
            entityType=entity_type,
            all_en_names=[en_name],
        )

    @classmethod
    def create_from_entity_data(cls, entity_data: dict, entity_type: EntityType) -> "Entity":
        """
        Factory: create an Entity from raw JSON entity_data dict.
        Base implementation uses only en_name. Subclasses override to extract
        additional fields (e.g. ENumber extracts numberCategory, unit, context).
        """
        en_name = entity_data.get("en_name", "").strip()
        return cls.create_from_en_name(en_name, entity_type)

    def to_db_dict(self) -> Dict[str, Any]:
        """Returns only the db-persisted fields as a dictionary."""
        return self.model_dump(exclude_none=True)

    def to_full_dict(self) -> Dict[str, Any]:
        """Returns all fields including transient ones."""
        return self.model_dump(exclude_none=True, exclude_unset=False)

    @classmethod
    def get_db_field_names(cls) -> List[str]:
        """Returns list of field names that are persisted to db."""
        return [
            name for name, field_info in cls.model_fields.items()
            if not field_info.exclude
        ]

    @classmethod
    def get_transient_field_names(cls) -> List[str]:
        """Returns list of transient field names."""
        return [
            name for name, field_info in cls.model_fields.items()
            if field_info.exclude
        ]
