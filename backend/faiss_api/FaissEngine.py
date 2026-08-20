

import faiss
import pickle
import time
from datetime import datetime
from typing import List, Dict, Optional

from sentence_transformers import SentenceTransformer
import numpy as np

from backend.db.Collections import CollectionObjs


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
        self._index = None
        self.metadata = []
        # Mongo uploadDate of the index currently cached in self._index, used
        # to detect when a *different* process has repopulated the index so
        # this one can pick up the change without needing a restart.
        self._loaded_at: Optional[datetime] = None


    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def index(self):
        if self._index is None:
            if self._load_from_mongo():
                pass
            else:
                self._index = faiss.IndexFlatL2(self.dim)
                self.metadata = []
        return self._index

    def _load_from_mongo(self) -> bool:
        """
        Load and deserialize the FAISS index and metadata from the database via dbapi.

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        # Ask db API to load raw bytes from the db
        data = self.dbapi.load_faiss_index()
        if not data:
            # No data found in db
            return False

        index_bytes, metadata_bytes = data
        index_np_array = np.frombuffer(index_bytes, dtype='uint8')
        # # Deserialize the FAISS index bytes back into a FAISS index object
        self._index = faiss.deserialize_index(index_np_array)

        # Deserialize the metadata bytes back into a Python list using pickle
        self.metadata = pickle.loads(metadata_bytes)

        # Record what we just loaded is current as of Mongo's own timestamp
        # (not local wall-clock, so it's comparable across processes/machines).
        try:
            self._loaded_at = self.dbapi.get_faiss_index_upload_date()
        except Exception as e:
            print(f"[FaissEngine] Could not read FAISS index upload date: {e}")
            self._loaded_at = None

        print(f"[FaissEngine] Loaded index from Mongo: {self._index.ntotal} vectors, "
              f"{len(self.metadata)} metadata keys (uploaded {self._loaded_at}).")

        return True

    def refresh(self) -> bool:
        """
        Force-reload the FAISS index/metadata from Mongo, discarding whatever
        is cached in memory. Use this to pick up data populated by a
        different process/script without restarting this one.

        Returns True if a persisted index was found and loaded, False if
        Mongo has nothing persisted (in which case a fresh empty index is
        used, same as on first access).
        """
        self._index = None
        self.metadata = []
        self._loaded_at = None
        if self._load_from_mongo():
            return True
        self._index = faiss.IndexFlatL2(self.dim)
        return False

    def _refresh_if_stale(self) -> None:
        """
        Cheaply check Mongo for a newer persisted index than what's cached in
        memory (metadata-only query, no bytes downloaded) and reload if so.

        This is what lets a long-running process (e.g. a Streamlit server
        that never restarts between reruns, or one instantiated before data
        was populated) automatically pick up newly-populated data instead of
        silently returning zero results forever.
        """
        try:
            latest = self.dbapi.get_faiss_index_upload_date()
        except Exception as e:
            print(f"[FaissEngine] Could not check FAISS index freshness: {e}")
            return

        if latest is None:
            return  # nothing persisted in Mongo yet; keep whatever is in memory

        if self._index is None or self._loaded_at is None or latest > self._loaded_at:
            print(f"[FaissEngine] Newer FAISS index detected in Mongo "
                  f"(uploaded {latest}, last loaded {self._loaded_at}); reloading.")
            self._load_from_mongo()

    def _save_to_mongo(self):
        """
        Serialize the current FAISS index and metadata, then save them to the database via dbapi.
        """
        # Serialize the FAISS index to bytes using faiss helper.
        # faiss.serialize_index() returns a numpy uint8 ndarray, not a
        # bytes object, so it must be converted before handing it to
        # GridFS (which only accepts bytes/str/file-like objects).
        index_bytes = faiss.serialize_index(self.index).tobytes()

        # Serialize the Python metadata list to bytes using pickle
        metadata_bytes = pickle.dumps(self.metadata)

        # Delegate saving the serialized bytes to the db API's method
        self.dbapi.save_faiss_index(index_bytes, metadata_bytes)

        # What we just wrote is now the freshest copy, so keep _loaded_at in
        # sync — otherwise _refresh_if_stale() would immediately think its
        # own just-saved index is "stale" and reload it right back from Mongo.
        try:
            self._loaded_at = self.dbapi.get_faiss_index_upload_date()
        except Exception as e:
            print(f"[FaissEngine] Could not read FAISS index upload date after save: {e}")

    # faiss_engine.py  — only the changed/added methods shown

    def add_documents(self, docs: List[Dict[str, str]]):
        """
        One-off addition (small batches). Saves to Mongo after every call.
        For bulk population of thousands of docs, use populate_bulk() instead.
        """
        new_docs = self.get_new_docs(docs)
        if not new_docs:
            return

        texts = [doc["content"] for doc in new_docs]
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        self.index.add(embeddings)
        self.metadata.extend([doc["key"] for doc in new_docs])
        self._save_to_mongo()

    def populate_bulk(
            self,
            docs: List[Dict[str, str]],
            batch_size: int = 256,
            checkpoint_every: int = 1000,
    ):
        """
        Efficient bulk ingestion for thousands of documents.

        - Encodes in batches (GPU/CPU-friendly, uses SentenceTransformer parallelism).
        - Saves to Mongo only at checkpoints and at the end — not per document.
        - Skips already-indexed keys automatically, so safe to re-run after a crash.

        :param docs:              List of {"key": str, "content": str} dicts.
        :param batch_size:        Encoding batch size. 256 is a good default for CPU;
                                  raise to 512-1024 if you have a GPU.
        :param checkpoint_every:  Save to Mongo every N *new* documents added.
                                  Lower = safer on flaky connections; higher = faster.
        """
        new_docs = self.get_new_docs(docs)
        if not new_docs:
            print("[FaissEngine] Nothing new to index.")
            return

        total = len(new_docs)
        print(f"[FaissEngine] Indexing {total} new documents ({len(docs) - total} already present).")

        added_since_checkpoint = 0
        start_time = time.time()

        for batch_start in range(0, total, batch_size):
            batch = new_docs[batch_start: batch_start + batch_size]
            texts = [doc["content"] for doc in batch]

            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,  # we handle progress ourselves
                batch_size=batch_size,
            )

            self.index.add(embeddings)
            self.metadata.extend([doc["key"] for doc in batch])
            added_since_checkpoint += len(batch)

            # Progress log
            done = batch_start + len(batch)
            elapsed = time.time() - start_time
            rate = done / elapsed  # docs/sec
            eta = (total - done) / rate if rate > 0 else 0
            print(
                f"  {done}/{total} docs "
                f"({done * 100 // total}%)  "
                f"{rate:.1f} docs/s  "
                f"ETA {eta / 60:.1f} min"
            )

            # Checkpoint save — recovers gracefully if Mongo drops mid-run
            if added_since_checkpoint >= checkpoint_every:
                print(f"  [checkpoint] Saving to Mongo at {done} docs…")
                self._save_to_mongo()
                added_since_checkpoint = 0

        # Final save (always, even if last batch didn't hit the checkpoint threshold)
        print("[FaissEngine] Saving final index to Mongo…")
        self._save_to_mongo()
        elapsed = time.time() - start_time
        print(f"[FaissEngine] Done. {total} documents indexed in {elapsed / 60:.1f} min.")

    def clear_index(self):
        """
        Totally wipes the FAISS index: resets the in-memory index/metadata
        and deletes the persisted copy in the db (via dbapi), so a fresh,
        empty index is used from here on.
        """
        self._index = faiss.IndexFlatL2(self.dim)
        self.metadata = []
        self._loaded_at = None
        self.dbapi.clear_faiss_index()

    def get_new_docs(self, docs):
        existing_keys = set(self.metadata)

        duplicate_keys = [doc["key"] for doc in docs if doc["key"] in existing_keys]
        # if duplicate_keys:
        #     print(f"[FaissEngine] Skipped duplicate keys: {duplicate_keys}")

        new_docs = [doc for doc in docs if doc["key"] not in existing_keys]
        return new_docs

    def search(self, query: str, top_k: int = 100000) -> List[str]:
        # Cheap freshness check first: if a different process/script has
        # (re)populated the index since we last loaded it, pick that up now
        # instead of silently searching a stale/empty in-memory copy.
        self._refresh_if_stale()

        ntotal = self.index.ntotal
        if ntotal == 0:
            print("[FaissEngine] search() called but the index has 0 vectors "
                  "in memory — nothing has been indexed yet, or reload failed.")
            return []

        if len(self.metadata) != ntotal:
            print(f"[FaissEngine] WARNING: metadata length ({len(self.metadata)}) "
                  f"does not match index size ({ntotal}); some results may be dropped.")

        query_vec = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_vec, top_k)

        # Return only the reference keys
        results = [self.metadata[i] for i in indices[0] if 0 <= i < len(self.metadata)]

        if not results:
            print(f"[FaissEngine] search({query!r}) matched 0 keys out of "
                  f"{ntotal} indexed vectors (top_k={top_k}).")

        return results

