# bs"d - lehagdil torah velahadir

"""
Number Search Handler.

Concrete implementation of BaseEntitySearchHandler for Number entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.ENumber import ENumber
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class NumberSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Number entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.ENumber

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getNumberSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Number transient fields.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in ENumber.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display Number-specific DB fields."""
        if not isinstance(entity, ENumber):
            return []

        fields = []
        if entity.numberCategory:
            fields.append(("entity_fields.numberCategory", entity.numberCategory.value))
        if entity.en_unit:
            fields.append(("entity_fields.en_unit", entity.en_unit))
        if entity.en_context:
            fields.append(("entity_fields.en_context", entity.en_context))
        return fields
