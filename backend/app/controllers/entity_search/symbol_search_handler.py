# bs"d - lehagdil torah velahadir

"""
Symbol Search Handler.

Concrete implementation of BaseEntitySearchHandler for Symbol entities.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.ESymbol import ESymbol
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class SymbolSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Symbol entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.ESymbol

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getSymbolSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Symbol transient fields.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in ESymbol.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display Symbol-specific DB fields."""
        if not isinstance(entity, ESymbol):
            return []

        fields = []
        if entity.symbolType:
            fields.append(("entity_fields.symbolType", entity.symbolType.value))
        return fields

    def get_metadata_badges(self, entity: Entity) -> List[Dict]:
        """Colorful, icon-based badge for Symbol metadata: symbol type.
        Icon/color come directly from the SymbolType enum member."""
        if not isinstance(entity, ESymbol) or not entity.symbolType:
            return []

        return [{
            "icon": entity.symbolType.icon,
            "text": entity.symbolType.value,
            "label_key": None,
            "color": entity.symbolType.color,
        }]
