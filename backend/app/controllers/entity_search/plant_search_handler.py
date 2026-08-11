# bs"d - lehagdil torah velahadir

"""
Plant Search Handler.

Concrete implementation of BaseEntitySearchHandler for Plant entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.EPlant import EPlant
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class PlantSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Plant entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.EPlant

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getPlantSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Plant transient fields.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in EPlant.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display Plant-specific DB fields.  EPlant has no extra db fields beyond Entity base."""
        if not isinstance(entity, EPlant):
            return []
        # EPlant has no extra db-stored fields beyond the base Entity fields.
        return []
