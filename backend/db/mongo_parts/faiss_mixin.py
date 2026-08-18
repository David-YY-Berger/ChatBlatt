from typing import Optional, Tuple

import gridfs

from backend.db.Collections import CollectionObjs

# GridFS filenames used to identify the (single, latest) persisted FAISS index/metadata.
_FAISS_INDEX_FILENAME = "faiss_index"
_METADATA_FILENAME = "metadata"


class FaissMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    def _get_faiss_gridfs(self) -> gridfs.GridFS:
        # The serialized FAISS index/metadata routinely exceed MongoDB's 16MB
        # per-document limit once the index grows large, so we store them via
        # GridFS (which transparently chunks large files) instead of as plain
        # document fields.
        database = self.get_collection(CollectionObjs.FS).database
        return gridfs.GridFS(database, collection=CollectionObjs.FS.name)

    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes) -> None:
        fs = self._get_faiss_gridfs()

        # Remove previous versions first so we don't accumulate orphaned files
        # (GridFS has no upsert semantics; each put() creates a new file).
        for old_file in fs.find({"filename": {"$in": [_FAISS_INDEX_FILENAME, _METADATA_FILENAME]}}):
            fs.delete(old_file._id)

        fs.put(index_bytes, filename=_FAISS_INDEX_FILENAME)
        fs.put(metadata_bytes, filename=_METADATA_FILENAME)

    def load_faiss_index(self) -> Optional[Tuple[bytes, bytes]]:
        fs = self._get_faiss_gridfs()

        index_file = fs.find_one({"filename": _FAISS_INDEX_FILENAME}, sort=[("uploadDate", -1)])
        metadata_file = fs.find_one({"filename": _METADATA_FILENAME}, sort=[("uploadDate", -1)])

        if index_file is None or metadata_file is None:
            return None

        return index_file.read(), metadata_file.read()

    def clear_faiss_index(self) -> None:
        """Remove all persisted FAISS index/metadata files from GridFS."""
        fs = self._get_faiss_gridfs()
        for grid_out in fs.find():
            fs.delete(grid_out._id)


