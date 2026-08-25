from datetime import datetime
from typing import Dict, Optional, Tuple

import gridfs

from backend.db.Collections import CollectionObjs, Collection
from backend.similarity_search_api.constants import KIND_FAISS, KIND_BM25

# Every supported engine "kind" (see backend.similarity_search_api.constants)
# maps to the GridFS bucket (Collection) its files live in, and the exact
# filename templates used to identify the (single, latest) persisted index +
# metadata *per language*. Filenames are preserved exactly as they were
# before FAISS and BM25 were unified into this one generic mixin (including
# FAISS's own historically slightly-asymmetric metadata filename), so
# nothing needs to be re-populated as a result of this refactor.
_KIND_COLLECTIONS: Dict[str, Collection] = {
    KIND_FAISS: CollectionObjs.FS,
    KIND_BM25: CollectionObjs.BM25,
}
_KIND_FILENAME_TEMPLATES: Dict[str, Tuple[str, str]] = {
    KIND_FAISS: ("faiss_index_{lang}", "metadata_{lang}"),
    KIND_BM25: ("bm25_index_{lang}", "bm25_metadata_{lang}"),
}


class SimilarityIndexMongoMixin:
    """Generic GridFS-backed persistence for every text-similarity engine's
    index + metadata, keyed by (kind, lang). Replaces what used to be two
    near-identical copies of this logic (one for FAISS, one for BM25) — a
    change here (e.g. compression, a new engine "kind") now applies to
    every engine at once.
    """

    def get_collection(self, collection):
        raise NotImplementedError

    def _get_similarity_gridfs(self, kind: str) -> gridfs.GridFS:
        # Serialized index/metadata routinely exceed MongoDB's 16MB
        # per-document limit once the index/corpus grows large, so we store
        # them via GridFS (which transparently chunks large files) instead
        # of as plain document fields.
        collection = _KIND_COLLECTIONS[kind]
        database = self.get_collection(collection).database
        return gridfs.GridFS(database, collection=collection.name)

    @staticmethod
    def _similarity_filenames(kind: str, lang: str) -> Tuple[str, str]:
        index_template, metadata_template = _KIND_FILENAME_TEMPLATES[kind]
        return index_template.format(lang=lang), metadata_template.format(lang=lang)

    def save_similarity_index(self, kind: str, index_bytes: bytes, metadata_bytes: bytes, lang: str = "en") -> None:
        fs = self._get_similarity_gridfs(kind)
        index_filename, metadata_filename = self._similarity_filenames(kind, lang)

        # Remove previous versions first so we don't accumulate orphaned
        # files (GridFS has no upsert semantics; each put() creates a new
        # file).
        for old_file in fs.find({"filename": {"$in": [index_filename, metadata_filename]}}):
            fs.delete(old_file._id)

        fs.put(index_bytes, filename=index_filename)
        fs.put(metadata_bytes, filename=metadata_filename)

    def load_similarity_index(self, kind: str, lang: str = "en") -> Optional[Tuple[bytes, bytes]]:
        fs = self._get_similarity_gridfs(kind)
        index_filename, metadata_filename = self._similarity_filenames(kind, lang)

        index_file = fs.find_one({"filename": index_filename}, sort=[("uploadDate", -1)])
        metadata_file = fs.find_one({"filename": metadata_filename}, sort=[("uploadDate", -1)])

        if index_file is None or metadata_file is None:
            return None

        return index_file.read(), metadata_file.read()

    def clear_similarity_index(self, kind: str, lang: str = "en") -> None:
        """Remove the persisted index/metadata files for (kind, lang) from GridFS."""
        fs = self._get_similarity_gridfs(kind)
        index_filename, metadata_filename = self._similarity_filenames(kind, lang)
        for grid_out in fs.find({"filename": {"$in": [index_filename, metadata_filename]}}):
            fs.delete(grid_out._id)

    def get_similarity_index_upload_date(self, kind: str, lang: str = "en") -> Optional[datetime]:
        """Cheap freshness check: return just the uploadDate of the latest
        persisted index file for (kind, lang) (no bytes downloaded), so
        callers can tell whether an in-memory cache is stale without paying
        the cost of a full reload."""
        fs = self._get_similarity_gridfs(kind)
        index_filename, _ = self._similarity_filenames(kind, lang)
        index_file = fs.find_one({"filename": index_filename}, sort=[("uploadDate", -1)])
        return index_file.uploadDate if index_file is not None else None
