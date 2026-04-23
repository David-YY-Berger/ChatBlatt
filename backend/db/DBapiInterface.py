from abc import ABC, abstractmethod
from typing import Any, Dict

from backend.db.Collections import Collection
from backend.db.interface_parts.entity_interface import EntityInterfaceMixin
from backend.db.interface_parts.faiss_interface import FaissInterfaceMixin
from backend.db.interface_parts.relationship_interface import RelationshipInterfaceMixin
from backend.db.interface_parts.source_content_interface import SourceContentInterfaceMixin
from backend.db.interface_parts.source_metadata_interface import SourceMetadataInterfaceMixin


class DBapiInterface(
    SourceContentInterfaceMixin,
    FaissInterfaceMixin,
    EntityInterfaceMixin,
    RelationshipInterfaceMixin,
    SourceMetadataInterfaceMixin,
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
