from typing import Optional, Tuple

from bson import Binary

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators


class FaissMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes) -> None:
        faiss_index_binary = Binary(index_bytes)
        metadata_binary = Binary(metadata_bytes)

        self.get_collection(CollectionObjs.FS).update_one(
            {},
            {
                DBOperators.SET: {
                    DBFields.FAISS_INDEX: faiss_index_binary,
                    DBFields.METADATA: metadata_binary,
                }
            },
            upsert=True,
        )

    def load_faiss_index(self) -> Optional[Tuple[bytes, bytes]]:
        record = self.get_collection(CollectionObjs.FS).find_one({})
        if not record:
            return None

        index_bytes = bytes(record.get(DBFields.FAISS_INDEX)) if record.get(DBFields.FAISS_INDEX) else None
        metadata_bytes = bytes(record.get(DBFields.METADATA)) if record.get(DBFields.METADATA) else None

        if index_bytes is None or metadata_bytes is None:
            return None

        return index_bytes, metadata_bytes


