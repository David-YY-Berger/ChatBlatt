# bs'd
"""
FaissEngine: semantic/embedding text-similarity, backed by FAISS + a
SentenceTransformer encoder.

All the shared machinery (singleton/dbapi-refresh semantics, per-language
state, Mongo persistence/staleness handling, checkpointed bulk population,
clearing, and the search() contract) lives in BaseSimilarityEngine - this
class only plugs in the FAISS-specific parts: encoding text into vectors,
adding them to a faiss.Index, and (de)serializing that index.
"""

from typing import Any, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from backend.similarity_search_api.BaseSimilarityEngine import BaseSimilarityEngine
from backend.similarity_search_api.constants import KIND_FAISS, LANG_EN, LANG_HEB, SUPPORTED_LANGS

# Re-exported for backward compatibility - existing callers do e.g.
# `from backend.faiss_api.FaissEngine import FaissEngine, LANG_EN` or
# `FaissEngine.LANG_EN` (module-level access via `from backend.faiss_api
# import FaissEngine`). Both keep working unchanged.
__all__ = ["FaissEngine", "LANG_EN", "LANG_HEB", "SUPPORTED_LANGS"]


class FaissEngine(BaseSimilarityEngine):
    KIND = KIND_FAISS

    def __init__(self, dbapi, model_name="all-MiniLM-L6-v2", dim=384):
        """
        :param dbapi: An instance of DBapiMongoDB (must have dbs dict with FAISS db).
        :param model_name: SentenceTransformer model to use.
        :param dim: Dimensionality of the embedding vectors.
        """
        super().__init__(dbapi=dbapi)
        if not self._first_time_init:
            return  # model/dim already set on first construction; see BaseSimilarityEngine

        self.model_name = model_name
        self.dim = dim
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    # ------------------------------------------------------------------
    # BaseSimilarityEngine hooks
    # ------------------------------------------------------------------

    def _new_empty_index(self) -> faiss.Index:
        return faiss.IndexFlatL2(self.dim)

    def _serialize_index(self, index_obj: faiss.Index) -> bytes:
        # faiss.serialize_index() returns a numpy uint8 ndarray, not a
        # bytes object, so it must be converted before handing it to
        # GridFS (which only accepts bytes/str/file-like objects).
        return faiss.serialize_index(index_obj).tobytes()

    def _deserialize_index(self, index_bytes: bytes) -> faiss.Index:
        index_np_array = np.frombuffer(index_bytes, dtype='uint8')
        return faiss.deserialize_index(index_np_array)

    def _index_size(self, index_obj: faiss.Index) -> int:
        return index_obj.ntotal

    def _ingest(self, lang: str, index_obj: faiss.Index, texts: List[str]) -> None:
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        index_obj.add(embeddings)

    def _rank_all(self, lang: str, index_obj: faiss.Index, query: str, top_k: int) -> List[int]:
        query_vec = self.model.encode([query], convert_to_numpy=True)
        _distances, indices = index_obj.search(query_vec, top_k)
        return list(indices[0])
