# bs"d - lehagdil torah velahadir

"""
Food Search Handler.

Concrete implementation of BaseEntitySearchHandler for Food entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.EFood import EFood
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class FoodSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Food entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.EFood

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getFoodSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Food transient fields.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in EFood.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display Food-specific DB fields.  EFood has no extra db fields beyond Entity base."""
        if not isinstance(entity, EFood):
            return []
        # EFood has no extra db-stored fields beyond the base Entity fields.
        return []
