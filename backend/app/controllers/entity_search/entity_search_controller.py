# bs"d - lehagdil torah velahadir

"""
Entity Search Controller.

Abstract base class for entity search operations, with concrete implementations
per entity type. Each handler knows how to:
  1. Fetch select options (for the combobox)
  2. Fetch a full entity by key, with transient fields populated

Design: Extend BaseEntitySearchHandler for each entity type.
Currently implemented: PersonSearchHandler.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Type

from backend.app.controllers.entity_populator import get_populator
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.db.DBFactory import DBFactory
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class BaseEntitySearchHandler(ABC):
    """
    Abstract handler for entity search operations.

    Subclasses implement:
      - get_select_options(): returns list of EntitySelectOption for the combobox
      - get_entity_type(): returns the EntityType this handler manages
      - get_transient_field_labels(): returns ordered list of (field_name, display_label) for UI

    Shared logic:
      - get_full_entity(key): fetches entity + populates transient fields
    """

    def __init__(self, db: Optional[DBapiMongoDB] = None):
        self.db: DBapiMongoDB = db or DBFactory.get_prod_db_mongo()

    @abstractmethod
    def get_entity_type(self) -> EntityType:
        """The EntityType this handler manages."""
        ...

    @abstractmethod
    def get_select_options(self) -> List[EntitySelectOption]:
        """Fetch all select options for the combobox."""
        ...

    @abstractmethod
    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Returns ordered list of (field_name, display_label_key) for transient fields.
        display_label_key is a translation key like 'entity_fields.childOfFather'.
        """
        ...

    @abstractmethod
    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """
        Returns ordered list of (label, value_str) for the DB-stored fields
        to display in the entity detail view. Subclasses decide what to show.
        """
        ...

    def get_full_entity(self, entity_key: str) -> Optional[Entity]:
        """
        Fetch entity by key, then populate all transient fields from rels.
        Returns the hydrated entity, or None if not found.
        """
        entity = self.db.get_entity_by_key(entity_key)
        if entity is None:
            return None

        # Fetch all rels for this entity
        rels = self.db.get_rels_for_entity(entity_key)

        # Populate transient fields
        populator = get_populator(entity.entityType)
        if populator:
            entity = populator.populate(entity, rels, self.db)

        return entity



# ========================= Handler Registry =========================

from backend.app.controllers.entity_search.person_search_handler import PersonSearchHandler  # noqa: E402

_HANDLER_REGISTRY: Dict[str, Type[BaseEntitySearchHandler]] = {
    "people": PersonSearchHandler,
    # "places": PlaceSearchHandler,       # TODO
    # "nations": NationSearchHandler,     # TODO
    # "tribes": TribeSearchHandler,       # TODO
}


def get_entity_search_handler(entity_tab: str, db: Optional[DBapiMongoDB] = None) -> Optional[BaseEntitySearchHandler]:
    """
    Factory: get the appropriate handler for an entity tab key.
    Returns None if the tab is not yet implemented.
    """
    handler_cls = _HANDLER_REGISTRY.get(entity_tab)
    if handler_cls is None:
        return None
    return handler_cls(db=db)
