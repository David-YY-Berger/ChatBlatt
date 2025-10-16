import faiss
import pickle
from typing import List, Dict

from bson import Binary
from sentence_transformers import SentenceTransformer
import numpy as np

from BackEnd.DataPipeline.DB import DBapiInterface
from BackEnd.DataPipeline.DB.Collection import CollectionName


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
        :param dbapi: An instance of DBapiMongoDB (must have dbs dict with FAISS DB).
        :param model_name: SentenceTransformer model to use.
        :param dim: Dimensionality of the embedding vectors.
        """
        self.dbapi = dbapi

        # Check that the FAISS DB exists
        if CollectionName.FS.db_name not in self.dbapi.dbs:
            raise ValueError(f"The dbapi object must have a connected '{CollectionName.FS.db_name}' database")
        if self.dbapi.dbs[CollectionName.FS.db_name] is None:
            raise ValueError(f" the database is missing the collection '{CollectionName.FS.name}'")


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
        # Ask DB API to load raw bytes from the DB
        data = self.dbapi.load_faiss_index()
        if not data:
            # No data found in DB
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

        # Delegate saving the serialized bytes to the DB API's method
        self.dbapi.save_faiss_index(index_bytes, metadata_bytes)

    def add_documents(self, docs: List[Dict[str, str]]):

        new_docs = self.get_new_docs(docs)
        if not new_docs:
            return  # Nothing new to add

        texts = [doc["content"] for doc in new_docs]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        self.index.add(embeddings)

        # Store only the keys (references)
        self.metadata.extend([doc["key"] for doc in new_docs])

        self._save_to_mongo()

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

