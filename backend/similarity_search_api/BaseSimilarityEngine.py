# bs"d - lehagdil torah velahadir
"""
BaseSimilarityEngine: shared skeleton for every language-aware text-similarity
engine used by source search - currently FaissEngine (semantic/embedding
similarity) and BM25Engine (lexical/keyword similarity), fused together at
query time via Reciprocal Rank Fusion (see backend.common.RankFusion).

Both engines are:
  - Singletons - one shared in-memory instance *per concrete subclass* per
    process - but re-initializable with a fresh `dbapi` on every call (a new
    SourceSearchHandler() per request/rerun must not keep reading Mongo
    through a stale/disconnected client).
  - Keyed per-language (see backend.similarity_search_api.constants):
    each language has a fully independent index + metadata list + freshness
    timestamp, so populating, clearing or searching one language never
    touches another.
  - Lazily loaded from Mongo (via dbapi.load_similarity_index), with a cheap
    upload-date check (dbapi.get_similarity_index_upload_date) used to
    detect when a *different* process has repopulated the index so this one
    can pick up the change without needing a restart.
  - Bulk-populated with progress logging + periodic checkpoint saves, and
    fully clearable per-language or across every language at once.

Subclasses only need to plug in the handful of things that are genuinely
different between a semantic vector index and a lexical/keyword index:
  - what an empty index looks like                    (`_new_empty_index`)
  - how to (de)serialize it to/from bytes for Mongo    (`_serialize_index` /
                                                         `_deserialize_index`)
  - how many documents it currently holds              (`_index_size`)
  - how to add new documents' text into it              (`_ingest`)
  - how to rank the *entire* index against a query      (`_rank_all`)

Everything else - singleton/dbapi refresh semantics, per-language state
management, staleness checks, checkpointed bulk population, clearing, and
the search()/populate_bulk()/add_documents() call shapes (every engine
returns/accepts the exact same shapes) - lives here once. A change to e.g.
checkpoint logging, staleness detection, or the search() contract
automatically applies to every engine that extends this class.
"""

import pickle
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.db.Collections import CollectionObjs
from backend.similarity_search_api.constants import LANG_EN, SUPPORTED_LANGS

# Every supported engine persists to the same Mongo *database* (just
# different GridFS buckets within it - see similarity_index_mixin.py), so
# this one connectivity check covers every engine.
_REQUIRED_DB_NAME = CollectionObjs.FS.db_name


class BaseSimilarityEngine(ABC):
    #: Set by each concrete subclass (see backend.similarity_search_api.
    #: constants.KIND_*) - identifies this engine's persisted data to the db
    #: layer and in log lines.
    KIND: str = None

    # One singleton instance *per concrete subclass* - FaissEngine and
    # BM25Engine each get their own, fully independent instance, keyed by
    # class rather than sharing a single slot.
    _instances: Dict[type, "BaseSimilarityEngine"] = {}

    def __new__(cls, *args, **kwargs):
        if cls not in BaseSimilarityEngine._instances:
            BaseSimilarityEngine._instances[cls] = super().__new__(cls)
        return BaseSimilarityEngine._instances[cls]

    def __init__(self, dbapi):
        """
        :param dbapi: An instance of DBapiMongoDB (must have a connected
                       "Faiss" database - see _REQUIRED_DB_NAME - which
                       hosts every similarity engine's GridFS data).
        """
        if not self.KIND:
            raise NotImplementedError(f"{type(self).__name__} must set a class-level KIND")

        # NOTE: this engine is a singleton (one shared index per process),
        # but the dbapi passed in must always be refreshed - previously this
        # was skipped whenever the engine was already initialized, so a
        # later e.g. `FaissEngine(dbapi=new_db_api)` call (a new
        # SourceSearchHandler() created per request/rerun) silently kept
        # whatever dbapi the *first* call happened to use - search() could
        # then be reading Mongo through a stale/disconnected client.
        self.dbapi = dbapi

        if _REQUIRED_DB_NAME not in self.dbapi.dbs:
            raise ValueError(f"The dbapi object must have a connected '{_REQUIRED_DB_NAME}' database")
        if self.dbapi.dbs[_REQUIRED_DB_NAME] is None:
            raise ValueError(f"The dbapi object's '{_REQUIRED_DB_NAME}' database is not connected")

        # Subclasses that accept extra constructor args (e.g. FaissEngine's
        # model_name/dim) need to know whether *this* call is the one that
        # should (re)set up their own one-time state, exactly like the
        # generic state below - so we compute and expose that here rather
        # than each subclass re-implementing the same guard.
        self._first_time_init = not getattr(self, "_initialized", False)
        self._initialized = True
        if not self._first_time_init:
            return  # index/metadata already set up; dbapi has just been refreshed above

        # Per-language state: one independent index object + metadata list +
        # freshness timestamp for each entry in SUPPORTED_LANGS.
        self._index_state: Dict[str, Any] = {}
        self._metadata: Dict[str, List[str]] = {}
        self._loaded_at: Dict[str, Optional[datetime]] = {}
        self._on_init()

    # ------------------------------------------------------------------
    # Hooks with no-op defaults - override only if a subclass needs them.
    # ------------------------------------------------------------------

    def _on_init(self) -> None:
        """Extra one-time, per-subclass setup beyond the generic
        per-language state above (e.g. BM25's lazily-built-scorer cache).
        Called exactly once, on first construction. No-op by default."""

    def _on_index_replaced(self, lang: str) -> None:
        """Called whenever self._index_state[lang] is replaced wholesale
        (fresh empty / loaded from Mongo / cleared) rather than mutated in
        place by `_ingest`, so subclasses with derived caches keyed off the
        old object's identity (e.g. BM25's lazily-built scorer) know to
        invalidate them. No-op by default."""

    # ------------------------------------------------------------------
    # Abstract hooks - the only genuinely engine-specific logic.
    # ------------------------------------------------------------------

    @abstractmethod
    def _new_empty_index(self) -> Any:
        """Return a brand-new, empty index object for one language."""

    @abstractmethod
    def _serialize_index(self, index_obj: Any) -> bytes:
        """Serialize one language's index object to bytes for persistence."""

    @abstractmethod
    def _deserialize_index(self, index_bytes: bytes) -> Any:
        """Deserialize bytes (as produced by `_serialize_index`) back into
        a live index object."""

    @abstractmethod
    def _index_size(self, index_obj: Any) -> int:
        """Number of documents currently held in `index_obj`."""

    @abstractmethod
    def _ingest(self, lang: str, index_obj: Any, texts: List[str]) -> None:
        """Add `texts` (in the given order) into `index_obj`, mutating it
        in place. Called with batches of new documents' cleaned text
        content, both from add_documents() and populate_bulk()."""

    @abstractmethod
    def _rank_all(self, lang: str, index_obj: Any, query: str, top_k: int) -> List[int]:
        """Rank every document in `index_obj` against `query`, best-first,
        and return up to `top_k` positional indices into that language's
        metadata list."""

    # ------------------------------------------------------------------
    # Shared machinery - identical for every engine.
    # ------------------------------------------------------------------

    @classmethod
    def _check_lang(cls, lang: str) -> str:
        if lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported {cls.KIND} language '{lang}'; expected one of {SUPPORTED_LANGS}")
        return lang

    def _ensure_loaded(self, lang: str) -> None:
        """Make sure an index/metadata list is cached in memory for `lang`,
        loading from Mongo if available or starting a fresh empty one."""
        lang = self._check_lang(lang)
        if lang in self._index_state:
            return
        if not self._load_from_mongo(lang):
            self._index_state[lang] = self._new_empty_index()
            self._metadata[lang] = []
            self._on_index_replaced(lang)

    def _get_index(self, lang: str = LANG_EN) -> Any:
        self._ensure_loaded(lang)
        return self._index_state[lang]

    def _get_metadata(self, lang: str = LANG_EN) -> List[str]:
        self._ensure_loaded(lang)
        return self._metadata[lang]

    def _load_from_mongo(self, lang: str) -> bool:
        """
        Load and deserialize the index and metadata for `lang` from the
        database via dbapi.

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        data = self.dbapi.load_similarity_index(self.KIND, lang=lang)
        if not data:
            return False

        index_bytes, metadata_bytes = data
        self._index_state[lang] = self._deserialize_index(index_bytes)
        self._metadata[lang] = pickle.loads(metadata_bytes)
        self._on_index_replaced(lang)

        # Record what we just loaded is current as of Mongo's own timestamp
        # (not local wall-clock, so it's comparable across processes/machines).
        try:
            self._loaded_at[lang] = self.dbapi.get_similarity_index_upload_date(self.KIND, lang=lang)
        except Exception as e:
            print(f"[{self.KIND}:{lang}] Could not read index upload date: {e}")
            self._loaded_at[lang] = None

        print(f"[{self.KIND}:{lang}] Loaded index from Mongo: "
              f"{self._index_size(self._index_state[lang])} documents, "
              f"{len(self._metadata[lang])} metadata keys (uploaded {self._loaded_at[lang]}).")
        return True

    def refresh(self, lang: str = LANG_EN) -> bool:
        """
        Force-reload the index/metadata for `lang` from Mongo, discarding
        whatever is cached in memory. Use this to pick up data populated by
        a different process/script without restarting this one.

        Returns True if a persisted index was found and loaded, False if
        Mongo has nothing persisted (in which case a fresh empty index is
        used, same as on first access).
        """
        lang = self._check_lang(lang)
        self._index_state.pop(lang, None)
        self._metadata.pop(lang, None)
        self._loaded_at.pop(lang, None)
        if self._load_from_mongo(lang):
            return True
        self._index_state[lang] = self._new_empty_index()
        self._metadata[lang] = []
        self._on_index_replaced(lang)
        return False

    def _refresh_if_stale(self, lang: str) -> None:
        """
        Cheaply check Mongo for a newer persisted index than what's cached
        in memory (metadata-only query, no bytes downloaded) and reload if
        so.

        This is what lets a long-running process (e.g. a Streamlit server
        that never restarts between reruns, or one instantiated before data
        was populated) automatically pick up newly-populated data instead of
        silently returning zero results forever.
        """
        try:
            latest = self.dbapi.get_similarity_index_upload_date(self.KIND, lang=lang)
        except Exception as e:
            print(f"[{self.KIND}:{lang}] Could not check index freshness: {e}")
            return

        if latest is None:
            return  # nothing persisted in Mongo yet; keep whatever is in memory

        loaded_at = self._loaded_at.get(lang)
        if lang not in self._index_state or loaded_at is None or latest > loaded_at:
            print(f"[{self.KIND}:{lang}] Newer index detected in Mongo "
                  f"(uploaded {latest}, last loaded {loaded_at}); reloading.")
            self._load_from_mongo(lang)

    def _save_to_mongo(self, lang: str) -> None:
        """
        Serialize the current index and metadata for `lang`, then save them
        to the database via dbapi.
        """
        index_bytes = self._serialize_index(self._index_state[lang])
        metadata_bytes = pickle.dumps(self._metadata[lang])
        self.dbapi.save_similarity_index(self.KIND, index_bytes, metadata_bytes, lang=lang)

        # What we just wrote is now the freshest copy, so keep _loaded_at in
        # sync — otherwise _refresh_if_stale() would immediately think its
        # own just-saved index is "stale" and reload it right back from Mongo.
        try:
            self._loaded_at[lang] = self.dbapi.get_similarity_index_upload_date(self.KIND, lang=lang)
        except Exception as e:
            print(f"[{self.KIND}:{lang}] Could not read index upload date after save: {e}")

    def get_new_docs(self, docs: List[Dict[str, str]], lang: str = LANG_EN) -> List[Dict[str, str]]:
        lang = self._check_lang(lang)
        existing_keys = set(self._get_metadata(lang))
        return [doc for doc in docs if doc["key"] not in existing_keys]

    def add_documents(self, docs: List[Dict[str, str]], lang: str = LANG_EN) -> None:
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

        index_obj = self._get_index(lang)
        self._ingest(lang, index_obj, [doc["content"] for doc in new_docs])
        self._metadata[lang].extend(doc["key"] for doc in new_docs)
        self._save_to_mongo(lang)

    def populate_bulk(
            self,
            docs: List[Dict[str, str]],
            lang: str = LANG_EN,
            batch_size: int = 256,
            checkpoint_every: int = 1000,
    ) -> None:
        """
        Efficient bulk ingestion for thousands of documents.

        - Ingests in batches via `_ingest` (GPU/CPU-friendly for FAISS's
          SentenceTransformer encoding; harmless chunking for BM25's cheap
          tokenization).
        - Saves to Mongo only at checkpoints and at the end — not per document.
        - Skips already-indexed keys automatically, so safe to re-run after a crash.

        :param docs:              List of {"key": str, "content": str} dicts.
        :param lang:              Which language-specific index to populate
                                  (one of SUPPORTED_LANGS). Each language has
                                  its own fully independent index/metadata.
        :param batch_size:        How many documents to `_ingest` per call.
                                  256 is a good default for CPU FAISS
                                  encoding; raise to 512-1024 with a GPU.
        :param checkpoint_every:  Save to Mongo every N *new* documents added.
                                  Lower = safer on flaky connections; higher = faster.
        """
        lang = self._check_lang(lang)
        new_docs = self.get_new_docs(docs, lang=lang)
        if not new_docs:
            print(f"[{self.KIND}:{lang}] Nothing new to index.")
            return

        total = len(new_docs)
        print(f"[{self.KIND}:{lang}] Indexing {total} new documents ({len(docs) - total} already present).")

        index_obj = self._get_index(lang)
        added_since_checkpoint = 0
        start_time = time.time()

        for batch_start in range(0, total, batch_size):
            batch = new_docs[batch_start: batch_start + batch_size]
            self._ingest(lang, index_obj, [doc["content"] for doc in batch])
            self._metadata[lang].extend(doc["key"] for doc in batch)
            added_since_checkpoint += len(batch)

            # Progress log
            done = batch_start + len(batch)
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0  # docs/sec
            eta = (total - done) / rate if rate > 0 else 0
            print(
                f"  [{self.KIND}:{lang}] {done}/{total} docs "
                f"({done * 100 // total}%)  "
                f"{rate:.1f} docs/s  "
                f"ETA {eta / 60:.1f} min"
            )

            # Checkpoint save — recovers gracefully if Mongo drops mid-run
            if added_since_checkpoint >= checkpoint_every:
                print(f"  [checkpoint:{self.KIND}:{lang}] Saving to Mongo at {done} docs…")
                self._save_to_mongo(lang)
                added_since_checkpoint = 0

        # Final save (always, even if last batch didn't hit the checkpoint threshold)
        print(f"[{self.KIND}:{lang}] Saving final index to Mongo…")
        self._save_to_mongo(lang)
        elapsed = time.time() - start_time
        print(f"[{self.KIND}:{lang}] Done. {total} documents indexed in {elapsed / 60:.1f} min.")

    def clear_index(self, lang: Optional[str] = None) -> None:
        """
        Totally wipes the index: resets the in-memory index/metadata and
        deletes the persisted copy in the db (via dbapi), so a fresh, empty
        index is used from here on.

        :param lang: Which language index to clear. If None (default),
                     clears *every* supported language's index.
        """
        langs = SUPPORTED_LANGS if lang is None else (self._check_lang(lang),)
        for l in langs:
            self._index_state[l] = self._new_empty_index()
            self._metadata[l] = []
            self._loaded_at[l] = None
            self._on_index_replaced(l)
            self.dbapi.clear_similarity_index(self.KIND, lang=l)

    def search(self, query: str, top_k: int = 100000, lang: str = LANG_EN) -> List[str]:
        """
        :param query:  Free-text query string.
        :param top_k:  Max number of ranked keys to return.
        :param lang:   Which language-specific index to search (one of
                       SUPPORTED_LANGS). Callers must pick the index matching
                       the language of `query`.
        :return:       Keys ranked best-first. Every concrete engine returns
                       this exact shape, so results from different engines
                       can be combined (e.g. via Reciprocal Rank Fusion — see
                       backend.common.RankFusion).
        """
        lang = self._check_lang(lang)

        # Cheap freshness check first: if a different process/script has
        # (re)populated the index since we last loaded it, pick that up now
        # instead of silently searching a stale/empty in-memory copy.
        self._refresh_if_stale(lang)

        index_obj = self._get_index(lang)
        metadata = self._get_metadata(lang)
        size = self._index_size(index_obj)

        if size == 0:
            print(f"[{self.KIND}:{lang}] search() called but the index has 0 documents "
                  "in memory — nothing has been indexed yet, or reload failed.")
            return []

        if len(metadata) != size:
            print(f"[{self.KIND}:{lang}] WARNING: metadata length ({len(metadata)}) "
                  f"does not match index size ({size}); some results may be dropped.")

        ranked_indices = self._rank_all(lang, index_obj, query, top_k)
        results = [metadata[i] for i in ranked_indices if 0 <= i < len(metadata)]

        if not results:
            print(f"[{self.KIND}:{lang}] search({query!r}) matched 0 keys out of "
                  f"{size} indexed documents (top_k={top_k}).")

        return results
