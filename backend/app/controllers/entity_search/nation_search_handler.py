# bs"d - lehagdil torah velahadir

"""
Nation Search Handler.

Concrete implementation of BaseEntitySearchHandler for Nation entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.ENation import ENation
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class NationSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Nation entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.ENation

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getNationSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Nation transient fields.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in ENation.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display Nation-specific DB fields.  ENation has no extra db fields beyond Entity base."""
        if not isinstance(entity, ENation):
            return []
        # ENation has no extra db-stored fields beyond the base Entity fields.
        return []

