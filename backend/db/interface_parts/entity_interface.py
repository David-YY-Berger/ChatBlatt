from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from backend.models.EntityObjects.Entity import Entity
from backend.models.Enums import EntityType


class EntityInterfaceMixin(ABC):
    @abstractmethod
    def is_entity_exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def insert_entity(self, entity: Entity) -> str:
        pass

    @abstractmethod
    def update_entity(self, entity: Entity) -> int:
        pass

    def upsert_entity(self, entity: Entity) -> str:
        if self.is_entity_exists(entity.key):
            self.update_entity(entity)
            return entity.key
        return self.insert_entity(entity)

    @abstractmethod
    def get_entity_by_key(self, key: str) -> Optional[Entity]:
        pass

    @abstractmethod
    def get_entities_by_keys(self, keys: List[str]) -> List[Entity]:
        pass

    @abstractmethod
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        pass

    @abstractmethod
    def get_all_entities(self) -> List[Entity]:
        pass

    @abstractmethod
    def search_entities_by_name(self, name: str, entity_type: Optional[EntityType] = None) -> List[Entity]:
        pass

    @abstractmethod
    def insert_entities_bulk(self, entities: List[Entity]) -> int:
        pass

    @abstractmethod
    def upsert_entities_bulk(self, entities: List[Entity]) -> Tuple[int, int]:
        pass

