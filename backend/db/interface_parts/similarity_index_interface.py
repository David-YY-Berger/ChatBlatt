from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple


class SimilarityIndexInterfaceMixin(ABC):
    """Persistence contract shared by every text-similarity engine (FAISS,
    BM25, and any future engine — see backend.similarity_search_api).

    Each engine's index/metadata is identified by a `kind` string (see
    backend.similarity_search_api.constants.KIND_*) plus a `lang` string,
    and is stored, cleared and refreshed completely independently of every
    other (kind, lang) pair — populating/clearing one never touches another.
    """

    @abstractmethod
    def save_similarity_index(self, kind: str, index_bytes: bytes, metadata_bytes: bytes, lang: str = "en") -> None:
        pass

    @abstractmethod
    def load_similarity_index(self, kind: str, lang: str = "en") -> Optional[Tuple[bytes, bytes]]:
        pass

    @abstractmethod
    def clear_similarity_index(self, kind: str, lang: str = "en") -> None:
        pass

    @abstractmethod
    def get_similarity_index_upload_date(self, kind: str, lang: str = "en") -> Optional[datetime]:
        """Return the upload timestamp of the currently persisted index file
        for (kind, lang), or None if nothing has been persisted yet. Used to
        detect, cheaply (without downloading the full index), whether an
        in-memory cache is stale relative to what's in the db."""
        pass
