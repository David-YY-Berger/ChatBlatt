# bs"d - lehagdil torah velahadir

"""
Place Search Handler.

Concrete implementation of BaseEntitySearchHandler for Place entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.EPlace import EPlace
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class PlaceSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Place entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.EPlace

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getPlaceSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Place transient fields.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in EPlace.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display Place-specific DB fields."""
        if not isinstance(entity, EPlace):
            return []

        fields = []
        if entity.placeType:
            fields.append(("entity_fields.placeType", entity.placeType.value))
        return fields

