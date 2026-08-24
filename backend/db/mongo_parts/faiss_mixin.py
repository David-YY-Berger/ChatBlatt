from datetime import datetime
from typing import Optional, Tuple

import gridfs

from backend.db.Collections import CollectionObjs

# GridFS filename templates used to identify the (single, latest) persisted
# FAISS index/metadata *per language*. Each supported language (see
# backend.faiss_api.FaissEngine.SUPPORTED_LANGS) gets its own pair of files,
# so English and Hebrew indexes are stored - and can be cleared/reloaded -
# completely independently of one another.
_FAISS_INDEX_FILENAME_TEMPLATE = "faiss_index_{lang}"
_METADATA_FILENAME_TEMPLATE = "metadata_{lang}"


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

    @staticmethod
    def _faiss_filenames(lang: str) -> Tuple[str, str]:
        return _FAISS_INDEX_FILENAME_TEMPLATE.format(lang=lang), _METADATA_FILENAME_TEMPLATE.format(lang=lang)

    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes, lang: str = "en") -> None:
        fs = self._get_faiss_gridfs()
        index_filename, metadata_filename = self._faiss_filenames(lang)

        # Remove previous versions first so we don't accumulate orphaned files
        # (GridFS has no upsert semantics; each put() creates a new file).
        for old_file in fs.find({"filename": {"$in": [index_filename, metadata_filename]}}):
            fs.delete(old_file._id)

        fs.put(index_bytes, filename=index_filename)
        fs.put(metadata_bytes, filename=metadata_filename)

    def load_faiss_index(self, lang: str = "en") -> Optional[Tuple[bytes, bytes]]:
        fs = self._get_faiss_gridfs()
        index_filename, metadata_filename = self._faiss_filenames(lang)

        index_file = fs.find_one({"filename": index_filename}, sort=[("uploadDate", -1)])
        metadata_file = fs.find_one({"filename": metadata_filename}, sort=[("uploadDate", -1)])

        if index_file is None or metadata_file is None:
            return None

        return index_file.read(), metadata_file.read()

    def clear_faiss_index(self, lang: str = "en") -> None:
        """Remove the persisted FAISS index/metadata files for `lang` from GridFS."""
        fs = self._get_faiss_gridfs()
        index_filename, metadata_filename = self._faiss_filenames(lang)
        for grid_out in fs.find({"filename": {"$in": [index_filename, metadata_filename]}}):
            fs.delete(grid_out._id)

    def get_faiss_index_upload_date(self, lang: str = "en") -> Optional[datetime]:
        """Cheap freshness check: return just the uploadDate of the latest
        persisted index file for `lang` (no bytes downloaded), so callers can
        tell whether an in-memory cache is stale without paying the cost of a
        full reload."""
        fs = self._get_faiss_gridfs()
        index_filename, _ = self._faiss_filenames(lang)
        index_file = fs.find_one({"filename": index_filename}, sort=[("uploadDate", -1)])
        return index_file.uploadDate if index_file is not None else None


