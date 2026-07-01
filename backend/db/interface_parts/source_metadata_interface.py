from abc import ABC, abstractmethod
from typing import List, Optional

from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata


class SourceMetadataInterfaceMixin(ABC):
    @abstractmethod
    def is_src_metadata_exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def insert_source_metadata(self, src_metadata: SourceMetadata) -> str:
        pass

    @abstractmethod
    def update_source_metadata(self, src_metadata: SourceMetadata) -> int:
        pass

    def upsert_source_metadata(self, src_metadata: SourceMetadata) -> str:
        if self.is_src_metadata_exists(src_metadata.key):
            self.update_source_metadata(src_metadata)
            return src_metadata.key
        return self.insert_source_metadata(src_metadata)

    @abstractmethod
    def get_source_metadata_by_key(self, key: str) -> Optional[SourceMetadata]:
        pass

    @abstractmethod
    def get_all_source_metadata(self) -> List[SourceMetadata]:
        pass

    @abstractmethod
    def get_source_metadata_by_entity_key(self, entity_key: str) -> List[SourceMetadata]:
        """
        Return all SourceMetadata documents whose entity_keys array contains
        the given entity_key.
        """
        pass

