

import faiss
import pickle
import time
from typing import List, Dict

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
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        # ... rest of your __init__ code
        """
        :param dbapi: An instance of DBapiMongoDB (must have dbs dict with FAISS db).
        :param model_name: SentenceTransformer model to use.
        :param dim: Dimensionality of the embedding vectors.
        """
        self.dbapi = dbapi

        # Check that the FAISS db exists
        if CollectionObjs.FS.db_name not in self.dbapi.dbs:
            raise ValueError(f"The dbapi object must have a connected '{CollectionObjs.FS.db_name}' database")
        if self.dbapi.dbs[CollectionObjs.FS.db_name] is None:
            raise ValueError(f" the database is missing the collection '{CollectionObjs.FS.name}'")


        self.model_name = model_name
        self.dim = dim
        self._model = None
        self._index = None
        self.metadata = []


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

        return True

    def _save_to_mongo(self):
        """
        Serialize the current FAISS index and metadata, then save them to the database via dbapi.
        """
        # Serialize the FAISS index to bytes using faiss helper
        index_bytes = faiss.serialize_index(self.index)

        # Serialize the Python metadata list to bytes using pickle
        metadata_bytes = pickle.dumps(self.metadata)

        # Delegate saving the serialized bytes to the db API's method
        self.dbapi.save_faiss_index(index_bytes, metadata_bytes)

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

    def get_new_docs(self, docs):
        existing_keys = set(self.metadata)

        duplicate_keys = [doc["key"] for doc in docs if doc["key"] in existing_keys]
        # if duplicate_keys:
        #     print(f"[FaissEngine] Skipped duplicate keys: {duplicate_keys}")

        new_docs = [doc for doc in docs if doc["key"] not in existing_keys]
        return new_docs

    def search(self, query: str, top_k: int = 5) -> List[str]:
        query_vec = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_vec, top_k)

        # Return only the reference keys
        return [self.metadata[i] for i in indices[0] if 0 <= i < len(self.metadata)]

