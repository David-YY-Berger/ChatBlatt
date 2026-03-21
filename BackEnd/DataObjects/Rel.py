# bs"d - lehagdil torah velahadir

from pydantic import BaseModel, Field
from typing import List, Any, Dict
from BackEnd.DataObjects.Enums import RelType


# Helper function for transient fields (excluded from serialization/DB)
def TransientField(default=None, default_factory=None, **kwargs):
    """Mark a field as transient - will be excluded from DB operations."""
    if default_factory is not None:
        return Field(default_factory=default_factory, exclude=True, **kwargs)
    return Field(default=default, exclude=True, **kwargs)


class Rel(BaseModel):
    """Relationship between two entities."""
    # db fields
    key: str
    term1: str  # key of Entity
    term2: str  # key of Entity
    rel_type: RelType

    # transient fields
    source_keys: List[str] = TransientField(default_factory=list)

    def to_db_dict(self) -> Dict[str, Any]:
        """Returns only the DB-persisted fields as a dictionary."""
        return self.model_dump(exclude_none=True)

    def to_full_dict(self) -> Dict[str, Any]:
        """Returns all fields including transient ones."""
        return self.model_dump(exclude_none=True, exclude_unset=False)

    @classmethod
    def get_db_field_names(cls) -> List[str]:
        """Returns list of field names that are persisted to DB."""
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
