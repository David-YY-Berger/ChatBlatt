from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, TypeVar

from backend.db.Collections import Collection
from backend.db.interface_parts.entity_interface import EntityInterfaceMixin
from backend.db.interface_parts.genealogy_interface import GenealogyInterfaceMixin
from backend.db.interface_parts.relationship_interface import RelationshipInterfaceMixin
from backend.db.interface_parts.similarity_index_interface import SimilarityIndexInterfaceMixin
from backend.db.interface_parts.source_content_interface import SourceContentInterfaceMixin
from backend.db.interface_parts.source_metadata_interface import SourceMetadataInterfaceMixin

T = TypeVar("T")


class DBapiInterface(
    SourceContentInterfaceMixin,
    SimilarityIndexInterfaceMixin,
    EntityInterfaceMixin,
    RelationshipInterfaceMixin,
    SourceMetadataInterfaceMixin,
    GenealogyInterfaceMixin,
    ABC,
):
    """Shared DB API contract, composed from per-domain mixins."""

    @abstractmethod
    def connect(self, connection_string: str) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def run_in_transaction(self, callback: Callable[[], T]) -> T:
        """
        Runs callback() as one transaction: all DB writes it makes are committed together
        when it returns, or none of them if it raises. Returns callback's result.
        """
        pass

    @abstractmethod
    def execute_raw_query(self, query: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def execute_query_with_collection(self, query: Dict[str, Any], collection: Collection):
        pass

    @abstractmethod
    def insert(self, collection: Collection, data: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def update(self, collection: Collection, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    def delete_instance(self, collection: Collection, query: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    def delete_collection(self, collection: Collection) -> int:
        pass
