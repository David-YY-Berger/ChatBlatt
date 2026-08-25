# bs'd
"""
BM25Engine: lexical/keyword text-similarity, backed by rank_bm25's
BM25Okapi, complementing FaissEngine's semantic/embedding similarity.

All the shared machinery (singleton/dbapi-refresh semantics, per-language
state, Mongo persistence/staleness handling, checkpointed bulk population,
clearing, and the search() contract) lives in BaseSimilarityEngine - this
class only plugs in the BM25-specific parts: tokenizing text, appending
token-lists to a raw corpus, and lazily (re)building the actual BM25Okapi
scorer from that corpus.

Why a from-scratch rebuild strategy instead of incremental add() (like
FAISS's IndexFlatL2.add()): rank_bm25's BM25Okapi has no incremental-update
API - its idf/avgdl statistics are a function of the *entire* corpus, so
they must be recomputed whenever the corpus changes. We therefore persist
the raw tokenized corpus (aligned with the metadata key list, same
convention as FAISS's persisted index) and only rebuild the actual
BM25Okapi scoring object lazily - cached per language until the corpus
changes again - not on every query.
"""

import re
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi

import pickle

from backend.similarity_search_api.BaseSimilarityEngine import BaseSimilarityEngine
from backend.similarity_search_api.constants import KIND_BM25, LANG_EN, LANG_HEB, SUPPORTED_LANGS

# Re-exported for backward compatibility - existing callers do e.g.
# `from backend.bm25_api.BM25Engine import BM25Engine, LANG_EN` or
# `BM25Engine.LANG_EN` (module-level access via `from backend.bm25_api
# import BM25Engine`). Both keep working unchanged.
__all__ = ["BM25Engine", "LANG_EN", "LANG_HEB", "SUPPORTED_LANGS", "tokenize"]

# A single generic tokenizer is used for both languages: lowercase, then
# split into "word" runs. Python's `re` module matches `\w` against Unicode
# letters (not just ASCII) by default for `str` patterns, so this correctly
# tokenizes Hebrew text too - especially since the corpus text passed in has
# already had niqqud/cantillation marks stripped upstream (see
# miscFuncs.clean_heb_text_from_html_tags), leaving plain Hebrew letters
# which `\w` matches. Lowercasing Hebrew is a harmless no-op (no case there).
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


class BM25Engine(BaseSimilarityEngine):
    KIND = KIND_BM25

    # ------------------------------------------------------------------
    # BaseSimilarityEngine hooks
    # ------------------------------------------------------------------

    def _on_init(self) -> None:
        # Lazily-(re)built BM25Okapi scorer, cached per language until the
        # corpus for that language changes (see _ingest/_on_index_replaced).
        self._bm25_models: Dict[str, Optional[BM25Okapi]] = {}

    def _on_index_replaced(self, lang: str) -> None:
        self._bm25_models[lang] = None

    def _new_empty_index(self) -> List[List[str]]:
        return []

    def _serialize_index(self, index_obj: List[List[str]]) -> bytes:
        return pickle.dumps(index_obj)

    def _deserialize_index(self, index_bytes: bytes) -> List[List[str]]:
        return pickle.loads(index_bytes)

    def _index_size(self, index_obj: List[List[str]]) -> int:
        return len(index_obj)

    def _ingest(self, lang: str, index_obj: List[List[str]], texts: List[str]) -> None:
        index_obj.extend(tokenize(text) for text in texts)
        self._bm25_models[lang] = None  # invalidate cached scorer; rebuilt lazily on next search

    def _rank_all(self, lang: str, index_obj: List[List[str]], query: str, top_k: int) -> List[int]:
        model = self._bm25_models.get(lang)
        if model is None and index_obj:
            model = BM25Okapi(index_obj)
            self._bm25_models[lang] = model
        if model is None:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = model.get_scores(query_tokens)
        return list(scores.argsort()[::-1][:top_k])
