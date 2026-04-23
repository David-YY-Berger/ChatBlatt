from abc import ABC, abstractmethod
from typing import Optional, Tuple


class FaissInterfaceMixin(ABC):
    @abstractmethod
    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes) -> None:
        pass

    @abstractmethod
    def load_faiss_index(self) -> Optional[Tuple[bytes, bytes]]:
        pass

