from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple


class BM25InterfaceMixin(ABC):
    """Persistence contract for the BM25 (lexical/keyword) similarity index.

    Mirrors FaissInterfaceMixin exactly, but for the BM25 index/metadata, so
    the two similarity layers can be populated, cleared and refreshed fully
    independently of one another.
    """

    @abstractmethod
    def save_bm25_index(self, index_bytes: bytes, metadata_bytes: bytes, lang: str = "en") -> None:
        pass

    @abstractmethod
    def load_bm25_index(self, lang: str = "en") -> Optional[Tuple[bytes, bytes]]:
        pass

    @abstractmethod
    def clear_bm25_index(self, lang: str = "en") -> None:
        pass

    @abstractmethod
    def get_bm25_index_upload_date(self, lang: str = "en") -> Optional[datetime]:
        """Return the upload timestamp of the currently persisted BM25 index
        file for `lang`, or None if nothing has been persisted yet. Used to
        detect, cheaply (without downloading the full index), whether an
        in-memory cache is stale relative to what's in the db."""
        pass
