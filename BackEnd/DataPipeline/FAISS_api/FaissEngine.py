import faiss
import pickle
from typing import List, Dict

from bson import Binary
from sentence_transformers import SentenceTransformer
import numpy as np

from BackEnd.DataPipeline.DB import DBapiInterface


class FaissEngine:
    def __init__(
        self,
        dbapi : DBapiInterface,
        model_name: str = "all-MiniLM-L6-v2",
        dim: int = 384,
    ):
        """
        :param dbapi: An instance of DBapiMongoDB (must have .db property).
        :param model_name: SentenceTransformer model to use.
        :param dim: Dimensionality of the embedding vectors.
        :param mongo_collection_name: MongoDB collection to store the index.
        """
        if not hasattr(dbapi, "db") or dbapi.db is None:
            raise ValueError("The dbapi object must have a connected .db attribute")

        self.model = SentenceTransformer(model_name)
        self.dim = dim
        self.dbapi = dbapi

        if self._load_from_mongo():
            pass
        else:
            self.index = faiss.IndexFlatL2(dim)
            self.metadata = []

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
        # Deserialize the FAISS index bytes back into a FAISS index object
        self.index = faiss.deserialize_index(index_np_array)

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
        return [self.metadata[i] for i in indices[0] if i < len(self.metadata)]

