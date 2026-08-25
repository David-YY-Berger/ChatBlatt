# bs'd
"""
BM25Engine: a lexical/keyword text-similarity layer that complements FAISS's
semantic-embedding similarity layer.

Architecturally this mirrors backend.faiss_api.FaissEngine as closely as
possible (singleton, one fully independent index + metadata list per
language, lazy-load from Mongo, staleness refresh, bulk/checkpointed
population, clear_index) so the two engines can be populated and queried the
same way and combined via Reciprocal Rank Fusion (see
backend.common.RankFusion) at query time. Populating/searching this index
never touches the FAISS index/metadata at all - the two are stored under
completely separate GridFS files (see backend.db.mongo_parts.bm25_mixin).

Why a from-scratch rebuild strategy instead of incremental add() (like
FAISS's IndexFlatL2.add()): rank_bm25's BM25Okapi has no incremental-update
API - its idf/avgdl statistics are a function of the *entire* corpus, so
they must be recomputed whenever the corpus changes. We therefore persist
the raw tokenized corpus (aligned with the metadata key list, same
convention as FAISS) and only rebuild the actual BM25Okapi scoring object
lazily (cached until the corpus changes again) - not on every query.
"""

import pickle
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi

from backend.db.Collections import CollectionObjs

# Supported BM25 index languages - kept identical to FaissEngine.SUPPORTED_LANGS
# so callers can pick the same `lang` for both engines.
LANG_EN = "en"
LANG_HEB = "heb"
SUPPORTED_LANGS = (LANG_EN, LANG_HEB)

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


class BM25Engine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, dbapi):
        """
        :param dbapi: An instance of DBapiMongoDB (must have dbs dict with FAISS db,
                       shared with FaissEngine - see BM25MongoMixin).
        """
        # Singleton (one shared in-memory index per process), but the dbapi
        # passed in must always be refreshed - see FaissEngine.__init__ for
        # the full rationale (a new SourceSearchHandler() per request/rerun
        # must not keep reading Mongo through a stale/disconnected client).
        self.dbapi = dbapi

        if CollectionObjs.BM25.db_name not in self.dbapi.dbs:
            raise ValueError(f"The dbapi object must have a connected '{CollectionObjs.BM25.db_name}' database")
        if self.dbapi.dbs[CollectionObjs.BM25.db_name] is None:
            raise ValueError(f" the database is missing the collection '{CollectionObjs.BM25.name}'")

        if getattr(self, "_initialized", False):
            return  # corpus/index/metadata already set up; dbapi has just been refreshed above
        self._initialized = True

        # Per-language state: one independent tokenized corpus + metadata
        # list + freshness timestamp for each entry in SUPPORTED_LANGS, plus
        # a lazily-(re)built BM25Okapi scoring object cached alongside it.
        self._corpus_tokens: Dict[str, List[List[str]]] = {}
        self._metadata: Dict[str, List[str]] = {}
        self._bm25: Dict[str, Optional[BM25Okapi]] = {}
        self._loaded_at: Dict[str, Optional[datetime]] = {}

    @staticmethod
    def _check_lang(lang: str) -> str:
        if lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported BM25 language '{lang}'; expected one of {SUPPORTED_LANGS}")
        return lang

    def _ensure_loaded(self, lang: str) -> None:
        """Make sure a corpus/metadata list is cached in memory for `lang`,
        loading from Mongo if available or starting a fresh empty one."""
        lang = self._check_lang(lang)
        if lang in self._corpus_tokens:
            return
        if not self._load_from_mongo(lang):
            self._corpus_tokens[lang] = []
            self._metadata[lang] = []
            self._bm25[lang] = None

    def _get_metadata(self, lang: str = LANG_EN) -> List[str]:
        self._ensure_loaded(lang)
        return self._metadata[lang]

    def _get_model(self, lang: str) -> Optional[BM25Okapi]:
        """Return the cached BM25Okapi scorer for `lang`, (re)building it
        from the tokenized corpus if it hasn't been built yet (e.g. right
        after a load/add). Returns None if the corpus is empty."""
        self._ensure_loaded(lang)
        if self._bm25.get(lang) is None:
            corpus = self._corpus_tokens[lang]
            self._bm25[lang] = BM25Okapi(corpus) if corpus else None
        return self._bm25[lang]

    def _load_from_mongo(self, lang: str) -> bool:
        """
        Load the tokenized corpus and metadata for `lang` from the database
        via dbapi. Returns True if loading was successful, False otherwise.
        """
        data = self.dbapi.load_bm25_index(lang=lang)
        if not data:
            return False

        corpus_bytes, metadata_bytes = data
        self._corpus_tokens[lang] = pickle.loads(corpus_bytes)
        self._metadata[lang] = pickle.loads(metadata_bytes)
        self._bm25[lang] = None  # rebuild lazily on next search/add

        try:
            self._loaded_at[lang] = self.dbapi.get_bm25_index_upload_date(lang=lang)
        except Exception as e:
            print(f"[BM25Engine:{lang}] Could not read BM25 index upload date: {e}")
            self._loaded_at[lang] = None

        print(f"[BM25Engine:{lang}] Loaded index from Mongo: {len(self._corpus_tokens[lang])} documents, "
              f"{len(self._metadata[lang])} metadata keys (uploaded {self._loaded_at[lang]}).")

        return True

    def refresh(self, lang: str = LANG_EN) -> bool:
        """
        Force-reload the BM25 corpus/metadata for `lang` from Mongo,
        discarding whatever is cached in memory. Mirrors
        FaissEngine.refresh() exactly.
        """
        lang = self._check_lang(lang)
        self._corpus_tokens.pop(lang, None)
        self._metadata.pop(lang, None)
        self._bm25.pop(lang, None)
        self._loaded_at.pop(lang, None)
        if self._load_from_mongo(lang):
            return True
        self._corpus_tokens[lang] = []
        self._metadata[lang] = []
        self._bm25[lang] = None
        return False

    def _refresh_if_stale(self, lang: str) -> None:
        """Cheaply check Mongo for a newer persisted index than what's cached
        in memory (metadata-only query, no bytes downloaded) and reload if
        so. Mirrors FaissEngine._refresh_if_stale() exactly."""
        try:
            latest = self.dbapi.get_bm25_index_upload_date(lang=lang)
        except Exception as e:
            print(f"[BM25Engine:{lang}] Could not check BM25 index freshness: {e}")
            return

        if latest is None:
            return  # nothing persisted in Mongo yet; keep whatever is in memory

        loaded_at = self._loaded_at.get(lang)
        if lang not in self._corpus_tokens or loaded_at is None or latest > loaded_at:
            print(f"[BM25Engine:{lang}] Newer BM25 index detected in Mongo "
                  f"(uploaded {latest}, last loaded {loaded_at}); reloading.")
            self._load_from_mongo(lang)

    def _save_to_mongo(self, lang: str):
        """Serialize the current tokenized corpus and metadata for `lang`,
        then save them to the database via dbapi."""
        index_bytes = pickle.dumps(self._corpus_tokens[lang])
        metadata_bytes = pickle.dumps(self._metadata[lang])
        self.dbapi.save_bm25_index(index_bytes, metadata_bytes, lang=lang)

        try:
            self._loaded_at[lang] = self.dbapi.get_bm25_index_upload_date(lang=lang)
        except Exception as e:
            print(f"[BM25Engine:{lang}] Could not read BM25 index upload date after save: {e}")

    def get_new_docs(self, docs, lang: str = LANG_EN):
        lang = self._check_lang(lang)
        existing_keys = set(self._get_metadata(lang))
        return [doc for doc in docs if doc["key"] not in existing_keys]

    def add_documents(self, docs: List[Dict[str, str]], lang: str = LANG_EN):
        """
        One-off addition (small batches). Saves to Mongo after every call.
        For bulk population of thousands of docs, use populate_bulk() instead.

        :param docs: List of {"key": str, "content": str} dicts.
        :param lang: Which language-specific index to add to (one of SUPPORTED_LANGS).
        """
        lang = self._check_lang(lang)
        new_docs = self.get_new_docs(docs, lang=lang)
        if not new_docs:
            return

        self._corpus_tokens[lang].extend(tokenize(doc["content"]) for doc in new_docs)
        self._metadata[lang].extend(doc["key"] for doc in new_docs)
        self._bm25[lang] = None  # invalidate cached scorer; rebuilt lazily
        self._save_to_mongo(lang)

    def populate_bulk(
            self,
            docs: List[Dict[str, str]],
            lang: str = LANG_EN,
            checkpoint_every: int = 1000,
    ):
        """
        Efficient bulk ingestion for thousands of documents.

        - Tokenizes every new doc, then saves to Mongo only at checkpoints
          and at the end - not per document.
        - Skips already-indexed keys automatically, so safe to re-run after
          a crash.
        - The BM25Okapi scorer itself is only (re)built lazily on first
          search()/get_new_docs() call after this returns, not once per
          checkpoint, since rebuilding requires a full corpus pass.

        :param docs:              List of {"key": str, "content": str} dicts.
        :param lang:              Which language-specific index to populate
                                  (one of SUPPORTED_LANGS). Each language has
                                  its own fully independent corpus/metadata.
        :param checkpoint_every:  Save to Mongo every N *new* documents added.
                                  Lower = safer on flaky connections; higher = faster.
        """
        lang = self._check_lang(lang)
        new_docs = self.get_new_docs(docs, lang=lang)
        if not new_docs:
            print(f"[BM25Engine:{lang}] Nothing new to index.")
            return

        total = len(new_docs)
        print(f"[BM25Engine:{lang}] Indexing {total} new documents ({len(docs) - total} already present).")

        added_since_checkpoint = 0
        start_time = time.time()

        for i, doc in enumerate(new_docs, start=1):
            self._corpus_tokens[lang].append(tokenize(doc["content"]))
            self._metadata[lang].append(doc["key"])
            added_since_checkpoint += 1

            if i % 500 == 0 or i == total:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (total - i) / rate if rate > 0 else 0
                print(
                    f"  [{lang}] {i}/{total} docs "
                    f"({i * 100 // total}%)  "
                    f"{rate:.1f} docs/s  "
                    f"ETA {eta / 60:.1f} min"
                )

            if added_since_checkpoint >= checkpoint_every:
                print(f"  [checkpoint:{lang}] Saving to Mongo at {i} docs…")
                self._bm25[lang] = None  # invalidate; not rebuilt here, just persisted
                self._save_to_mongo(lang)
                added_since_checkpoint = 0

        # Final save (always, even if the last batch didn't hit the checkpoint threshold)
        print(f"[BM25Engine:{lang}] Saving final index to Mongo…")
        self._bm25[lang] = None  # force a fresh rebuild on next search with the full corpus
        self._save_to_mongo(lang)
        elapsed = time.time() - start_time
        print(f"[BM25Engine:{lang}] Done. {total} documents indexed in {elapsed / 60:.1f} min.")

    def clear_index(self, lang: Optional[str] = None):
        """
        Totally wipes the BM25 index: resets the in-memory corpus/metadata
        and deletes the persisted copy in the db (via dbapi), so a fresh,
        empty index is used from here on. Mirrors FaissEngine.clear_index()
        exactly, and never touches the FAISS index/metadata.

        :param lang: Which language index to clear. If None (default),
                     clears *every* supported language's index.
        """
        langs = SUPPORTED_LANGS if lang is None else (self._check_lang(lang),)
        for l in langs:
            self._corpus_tokens[l] = []
            self._metadata[l] = []
            self._bm25[l] = None
            self._loaded_at[l] = None
            self.dbapi.clear_bm25_index(lang=l)

    def search(self, query: str, top_k: int = 100000, lang: str = LANG_EN) -> List[str]:
        """
        :param query:  Free-text query string.
        :param top_k:  Max number of ranked keys to return.
        :param lang:   Which language-specific index to search (one of
                       SUPPORTED_LANGS). Callers must pick the index matching
                       the language of `query`.
        :return:       Keys ranked best-first by BM25 score. Mirrors
                       FaissEngine.search()'s return shape exactly, so the
                       two can be fused with Reciprocal Rank Fusion.
        """
        lang = self._check_lang(lang)

        # Cheap freshness check first: if a different process/script has
        # (re)populated the index since we last loaded it, pick that up now.
        self._refresh_if_stale(lang)

        model = self._get_model(lang)
        metadata = self._get_metadata(lang)
        if model is None or not metadata:
            print(f"[BM25Engine:{lang}] search() called but the index has 0 documents "
                  "in memory — nothing has been indexed yet, or reload failed.")
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = model.get_scores(query_tokens)
        ranked_indices = scores.argsort()[::-1][:top_k]

        results = [metadata[i] for i in ranked_indices if 0 <= i < len(metadata)]

        if not results:
            print(f"[BM25Engine:{lang}] search({query!r}) matched 0 keys out of "
                  f"{len(metadata)} indexed documents (top_k={top_k}).")

        return results
