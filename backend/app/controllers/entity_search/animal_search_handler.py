# bs"d - lehagdil torah velahadir

"""
Animal Search Handler.

Concrete implementation of BaseEntitySearchHandler for Animal entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.EAnimal import EAnimal
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class AnimalSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Animal entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.EAnimal

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getAnimalSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Animal transient fields.
        """
        return [
            (field, f"entity_fields.{field}")
            for field in EAnimal.TRANSIENT_DISPLAY_FIELDS
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display Animal-specific DB fields.  EAnimal has no extra db fields beyond Entity base."""
        if not isinstance(entity, EAnimal):
            return []
        # EAnimal has no extra db-stored fields beyond the base Entity fields.
        return []
