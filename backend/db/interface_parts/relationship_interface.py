from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from backend.models.Rel import Rel


class RelationshipInterfaceMixin(ABC):
    @abstractmethod
    def is_rel_exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def insert_rel(self, rel: Rel) -> str:
        pass

    @abstractmethod
    def update_rel(self, rel: Rel) -> int:
        pass

    def upsert_rel(self, rel: Rel) -> str:
        if self.is_rel_exists(rel.key):
            self.update_rel(rel)
            return rel.key
        return self.insert_rel(rel)

    @abstractmethod
    def get_rel_by_key(self, key: str) -> Optional[Rel]:
        pass

    @abstractmethod
    def get_rels_by_keys(self, keys: List[str]) -> List[Rel]:
        pass

    @abstractmethod
    def get_rels_for_entity(self, entity_key: str) -> List[Rel]:
        pass

    @abstractmethod
    def get_all_rels(self) -> List[Rel]:
        pass

    @abstractmethod
    def insert_rels_bulk(self, rels: List[Rel]) -> int:
        pass

    @abstractmethod
    def upsert_rels_bulk(self, rels: List[Rel]) -> Tuple[int, int]:
        pass

