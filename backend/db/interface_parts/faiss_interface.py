from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple


class FaissInterfaceMixin(ABC):
    @abstractmethod
    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes) -> None:
        pass

    @abstractmethod
    def load_faiss_index(self) -> Optional[Tuple[bytes, bytes]]:
        pass

    @abstractmethod
    def clear_faiss_index(self) -> None:
        pass

    @abstractmethod
    def get_faiss_index_upload_date(self) -> Optional[datetime]:
        """Return the upload timestamp of the currently persisted FAISS index
        file, or None if nothing has been persisted yet. Used to detect,
        cheaply (without downloading the full index), whether an in-memory
        cache is stale relative to what's in the db."""
        pass

