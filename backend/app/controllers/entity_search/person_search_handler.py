# bs"d - lehagdil torah velahadir

"""
Person Search Handler.

Concrete implementation of BaseEntitySearchHandler for Person entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.EntityObjects.EPerson import EPerson
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class PersonSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Person entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.EPerson

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getPersonSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Person transient fields.
        Field names are taken directly from EPerson.TRANSIENT_DISPLAY_FIELDS so
        this method never needs to change when EPerson fields are renamed/reordered.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in EPerson.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display the Person-specific DB fields."""
        if not isinstance(entity, EPerson):
            return []

        fields = [
            ("entity_fields.timePeriod", entity.timePeriod.value if entity.timePeriod else ""),
            ("entity_fields.isWoman", "✓" if entity.isWoman else "✗"),
            ("entity_fields.isNonJew", "✓" if entity.isNonJew else "✗"),
            ("entity_fields.isGroup", "✓" if entity.isGroup else "✗"),
        ]
        if entity.roles:
            fields.append(("entity_fields.roles", ", ".join(r.value for r in entity.roles)))
        return fields

