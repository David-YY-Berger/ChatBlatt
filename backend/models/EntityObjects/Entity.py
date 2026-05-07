# bs"d - lehagdil torah velahadir

from pydantic import BaseModel, Field
from typing import List, Any, Dict

from backend.models.Enums import EntityType


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

    @classmethod
    def create_from_en_name(cls, en_name: str, entity_type: EntityType) -> "Entity":
        """Factory: create an Entity from just the English display name and type."""
        return cls(
            display_en_name=en_name,
            entityType=entity_type,
            all_en_names=[en_name],
        )

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
