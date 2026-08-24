

import faiss
import pickle
import time
from datetime import datetime
from typing import List, Dict, Optional

from sentence_transformers import SentenceTransformer
import numpy as np

from backend.db.Collections import CollectionObjs

# Supported FAISS index languages. Each language gets its own fully separate
# FAISS index + metadata list, persisted under its own GridFS filenames, so
# an English query is only ever ranked against English content and a Hebrew
# query only against Hebrew content.
LANG_EN = "en"
LANG_HEB = "heb"
SUPPORTED_LANGS = (LANG_EN, LANG_HEB)


class FaissEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, dbapi, model_name="all-MiniLM-L6-v2", dim=384):
        """
        :param dbapi: An instance of DBapiMongoDB (must have dbs dict with FAISS db).
        :param model_name: SentenceTransformer model to use.
        :param dim: Dimensionality of the embedding vectors.
        """
        # NOTE: FaissEngine is a singleton (one shared model/index per process),
        # but the dbapi passed in must always be refreshed. Previously this was
        # skipped whenever `_initialized` was already set, so a later
        # `FaissEngine(dbapi=new_db_api)` call (e.g. a new SourceSearchHandler()
        # created per request/rerun) silently kept whatever dbapi the *first*
        # call happened to use — search() could then be reading Mongo through a
        # stale/disconnected client while data was populated via a different one.
        self.dbapi = dbapi

        # Check that the FAISS db exists
        if CollectionObjs.FS.db_name not in self.dbapi.dbs:
            raise ValueError(f"The dbapi object must have a connected '{CollectionObjs.FS.db_name}' database")
        if self.dbapi.dbs[CollectionObjs.FS.db_name] is None:
            raise ValueError(f" the database is missing the collection '{CollectionObjs.FS.name}'")

        if getattr(self, "_initialized", False):
            return  # model/index/metadata already set up; dbapi has just been refreshed above
        self._initialized = True

        self.model_name = model_name
        self.dim = dim
        self._model = None
        # Per-language state: one independent FAISS index + metadata list +
        # freshness timestamp for each entry in SUPPORTED_LANGS.
        self._indexes: Dict[str, faiss.Index] = {}
        self._metadata: Dict[str, List[str]] = {}
        # Mongo uploadDate of the index currently cached per language, used
        # to detect when a *different* process has repopulated the index so
        # this one can pick up the change without needing a restart.
        self._loaded_at: Dict[str, Optional[datetime]] = {}


    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @staticmethod
    def _check_lang(lang: str) -> str:
        if lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported FAISS language '{lang}'; expected one of {SUPPORTED_LANGS}")
        return lang

    def _ensure_loaded(self, lang: str) -> None:
        """Make sure an index/metadata list is cached in memory for `lang`,
        loading from Mongo if available or starting a fresh empty one."""
        lang = self._check_lang(lang)
        if lang in self._indexes:
            return
        if not self._load_from_mongo(lang):
            self._indexes[lang] = faiss.IndexFlatL2(self.dim)
            self._metadata[lang] = []

    def _get_index(self, lang: str = LANG_EN):
        self._ensure_loaded(lang)
        return self._indexes[lang]

    def _get_metadata(self, lang: str = LANG_EN) -> List[str]:
        self._ensure_loaded(lang)
        return self._metadata[lang]

    def _load_from_mongo(self, lang: str) -> bool:
        """
        Load and deserialize the FAISS index and metadata for `lang` from the
        database via dbapi.

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        # Ask db API to load raw bytes from the db
        data = self.dbapi.load_faiss_index(lang=lang)
        if not data:
            # No data found in db
            return False

        index_bytes, metadata_bytes = data
        index_np_array = np.frombuffer(index_bytes, dtype='uint8')
        # Deserialize the FAISS index bytes back into a FAISS index object
        self._indexes[lang] = faiss.deserialize_index(index_np_array)

        # Deserialize the metadata bytes back into a Python list using pickle
        self._metadata[lang] = pickle.loads(metadata_bytes)

        # Record what we just loaded is current as of Mongo's own timestamp
        # (not local wall-clock, so it's comparable across processes/machines).
        try:
            self._loaded_at[lang] = self.dbapi.get_faiss_index_upload_date(lang=lang)
        except Exception as e:
            print(f"[FaissEngine:{lang}] Could not read FAISS index upload date: {e}")
            self._loaded_at[lang] = None

        print(f"[FaissEngine:{lang}] Loaded index from Mongo: {self._indexes[lang].ntotal} vectors, "
              f"{len(self._metadata[lang])} metadata keys (uploaded {self._loaded_at[lang]}).")

        return True

    def refresh(self, lang: str = LANG_EN) -> bool:
        """
        Force-reload the FAISS index/metadata for `lang` from Mongo,
        discarding whatever is cached in memory. Use this to pick up data
        populated by a different process/script without restarting this one.

        Returns True if a persisted index was found and loaded, False if
        Mongo has nothing persisted (in which case a fresh empty index is
        used, same as on first access).
        """
        lang = self._check_lang(lang)
        self._indexes.pop(lang, None)
        self._metadata.pop(lang, None)
        self._loaded_at.pop(lang, None)
        if self._load_from_mongo(lang):
            return True
        self._indexes[lang] = faiss.IndexFlatL2(self.dim)
        self._metadata[lang] = []
        return False

    def _refresh_if_stale(self, lang: str) -> None:
        """
        Cheaply check Mongo for a newer persisted index than what's cached in
        memory (metadata-only query, no bytes downloaded) and reload if so.

        This is what lets a long-running process (e.g. a Streamlit server
        that never restarts between reruns, or one instantiated before data
        was populated) automatically pick up newly-populated data instead of
        silently returning zero results forever.
        """
        try:
            latest = self.dbapi.get_faiss_index_upload_date(lang=lang)
        except Exception as e:
            print(f"[FaissEngine:{lang}] Could not check FAISS index freshness: {e}")
            return

        if latest is None:
            return  # nothing persisted in Mongo yet; keep whatever is in memory

        loaded_at = self._loaded_at.get(lang)
        if lang not in self._indexes or loaded_at is None or latest > loaded_at:
            print(f"[FaissEngine:{lang}] Newer FAISS index detected in Mongo "
                  f"(uploaded {latest}, last loaded {loaded_at}); reloading.")
            self._load_from_mongo(lang)

    def _save_to_mongo(self, lang: str):
        """
        Serialize the current FAISS index and metadata for `lang`, then save
        them to the database via dbapi.
        """
        # Serialize the FAISS index to bytes using faiss helper.
        # faiss.serialize_index() returns a numpy uint8 ndarray, not a
        # bytes object, so it must be converted before handing it to
        # GridFS (which only accepts bytes/str/file-like objects).
        index_bytes = faiss.serialize_index(self._get_index(lang)).tobytes()

        # Serialize the Python metadata list to bytes using pickle
        metadata_bytes = pickle.dumps(self._metadata[lang])

        # Delegate saving the serialized bytes to the db API's method
        self.dbapi.save_faiss_index(index_bytes, metadata_bytes, lang=lang)

        # What we just wrote is now the freshest copy, so keep _loaded_at in
        # sync — otherwise _refresh_if_stale() would immediately think its
        # own just-saved index is "stale" and reload it right back from Mongo.
        try:
            self._loaded_at[lang] = self.dbapi.get_faiss_index_upload_date(lang=lang)
        except Exception as e:
            print(f"[FaissEngine:{lang}] Could not read FAISS index upload date after save: {e}")

    # faiss_engine.py  — only the changed/added methods shown

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

        texts = [doc["content"] for doc in new_docs]
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        self._get_index(lang).add(embeddings)
        self._metadata[lang].extend([doc["key"] for doc in new_docs])
        self._save_to_mongo(lang)

    def populate_bulk(
            self,
            docs: List[Dict[str, str]],
            lang: str = LANG_EN,
            batch_size: int = 256,
            checkpoint_every: int = 1000,
    ):
        """
        Efficient bulk ingestion for thousands of documents.

        - Encodes in batches (GPU/CPU-friendly, uses SentenceTransformer parallelism).
        - Saves to Mongo only at checkpoints and at the end — not per document.
        - Skips already-indexed keys automatically, so safe to re-run after a crash.

        :param docs:              List of {"key": str, "content": str} dicts.
        :param lang:              Which language-specific index to populate
                                  (one of SUPPORTED_LANGS). Each language has
                                  its own fully independent index/metadata.
        :param batch_size:        Encoding batch size. 256 is a good default for CPU;
                                  raise to 512-1024 if you have a GPU.
        :param checkpoint_every:  Save to Mongo every N *new* documents added.
                                  Lower = safer on flaky connections; higher = faster.
        """
        lang = self._check_lang(lang)
        new_docs = self.get_new_docs(docs, lang=lang)
        if not new_docs:
            print(f"[FaissEngine:{lang}] Nothing new to index.")
            return

        total = len(new_docs)
        print(f"[FaissEngine:{lang}] Indexing {total} new documents ({len(docs) - total} already present).")

        added_since_checkpoint = 0
        start_time = time.time()
        index = self._get_index(lang)

        for batch_start in range(0, total, batch_size):
            batch = new_docs[batch_start: batch_start + batch_size]
            texts = [doc["content"] for doc in batch]

            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,  # we handle progress ourselves
                batch_size=batch_size,
            )

            index.add(embeddings)
            self._metadata[lang].extend([doc["key"] for doc in batch])
            added_since_checkpoint += len(batch)

            # Progress log
            done = batch_start + len(batch)
            elapsed = time.time() - start_time
            rate = done / elapsed  # docs/sec
            eta = (total - done) / rate if rate > 0 else 0
            print(
                f"  [{lang}] {done}/{total} docs "
                f"({done * 100 // total}%)  "
                f"{rate:.1f} docs/s  "
                f"ETA {eta / 60:.1f} min"
            )

            # Checkpoint save — recovers gracefully if Mongo drops mid-run
            if added_since_checkpoint >= checkpoint_every:
                print(f"  [checkpoint:{lang}] Saving to Mongo at {done} docs…")
                self._save_to_mongo(lang)
                added_since_checkpoint = 0

        # Final save (always, even if last batch didn't hit the checkpoint threshold)
        print(f"[FaissEngine:{lang}] Saving final index to Mongo…")
        self._save_to_mongo(lang)
        elapsed = time.time() - start_time
        print(f"[FaissEngine:{lang}] Done. {total} documents indexed in {elapsed / 60:.1f} min.")

    def clear_index(self, lang: Optional[str] = None):
        """
        Totally wipes the FAISS index: resets the in-memory index/metadata
        and deletes the persisted copy in the db (via dbapi), so a fresh,
        empty index is used from here on.

        :param lang: Which language index to clear. If None (default),
                     clears *every* supported language's index.
        """
        langs = SUPPORTED_LANGS if lang is None else (self._check_lang(lang),)
        for l in langs:
            self._indexes[l] = faiss.IndexFlatL2(self.dim)
            self._metadata[l] = []
            self._loaded_at[l] = None
            self.dbapi.clear_faiss_index(lang=l)

    def get_new_docs(self, docs, lang: str = LANG_EN):
        lang = self._check_lang(lang)
        existing_keys = set(self._get_metadata(lang))

        duplicate_keys = [doc["key"] for doc in docs if doc["key"] in existing_keys]
        # if duplicate_keys:
        #     print(f"[FaissEngine] Skipped duplicate keys: {duplicate_keys}")

        new_docs = [doc for doc in docs if doc["key"] not in existing_keys]
        return new_docs

    def search(self, query: str, top_k: int = 100000, lang: str = LANG_EN) -> List[str]:
        """
        :param query:  Free-text query string.
        :param top_k:  Max number of ranked keys to return.
        :param lang:   Which language-specific index to search (one of
                       SUPPORTED_LANGS). Callers must pick the index matching
                       the language of `query`.
        """
        lang = self._check_lang(lang)

        # Cheap freshness check first: if a different process/script has
        # (re)populated the index since we last loaded it, pick that up now
        # instead of silently searching a stale/empty in-memory copy.
        self._refresh_if_stale(lang)

        index = self._get_index(lang)
        ntotal = index.ntotal
        if ntotal == 0:
            print(f"[FaissEngine:{lang}] search() called but the index has 0 vectors "
                  "in memory — nothing has been indexed yet, or reload failed.")
            return []

        metadata = self._metadata[lang]
        if len(metadata) != ntotal:
            print(f"[FaissEngine:{lang}] WARNING: metadata length ({len(metadata)}) "
                  f"does not match index size ({ntotal}); some results may be dropped.")

        query_vec = self.model.encode([query], convert_to_numpy=True)
        distances, indices = index.search(query_vec, top_k)

        # Return only the reference keys
        results = [metadata[i] for i in indices[0] if 0 <= i < len(metadata)]

        if not results:
            print(f"[FaissEngine:{lang}] search({query!r}) matched 0 keys out of "
                  f"{ntotal} indexed vectors (top_k={top_k}).")

        return results

