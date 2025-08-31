from bson import Binary
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from typing import Any, Dict, List, Optional, Tuple

from BackEnd.DataPipeline.DB.CollectionName import CollectionName
from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.General.Decorators import singleton
from BackEnd.General.Logger import Logger
from typing_extensions import override

from BackEnd.DataObjects.SourceClasses import Source

@singleton
class DBapiMongoDB(DBapiInterface):
    """
    A concrete implementation of DBapiInterface for MongoDB.
    """

    def __init__(self, connection_string: str = None):

        self.client = None
        self.db_sources = None
        self.db_faiss = None
        self.connection_string = connection_string
        self.logger = Logger()

        if connection_string:
            self.connect(connection_string)

    @override
    def connect(self, connection_string: str) -> None:
        """
        Connect to the MongoDB database.
        """
        self.connection_string = connection_string
        self.client = MongoClient(connection_string, server_api=ServerApi('1'))
        try:
            self.client.admin.command('ping')
            self.logger.debug("Connected to the database")
        except Exception as e:
            print(f"Failed to connect: {e}")
            raise ConnectionError(f"Failed to connect: {e}")


        self.db_sources = self.client.get_database('Sources')
        self.db_faiss = self.client.get_database('Faiss')

    @override
    def disconnect(self) -> None:
        """
        Close the MongoDB database connection.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db_sources = None

    @override
    def execute_raw_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query on a MongoDB collection and return results.
        """
        collection_name = query.get('collection')
        query_filter = query.get('filter', {})
        if collection_name:
            collection = self.db_sources[collection_name]
            return list(collection.find(query_filter))
        return []

    @override
    def insert(self, collection_name: str, data: Dict[str, Any]) -> str:
        """
        Insert data into the collection_name collection.
        """
        if self.db_sources is None:
            raise Exception("Database connection is not established.")
        result = self.db_sources.get_collection(collection_name).insert_one(data)
        return str(result.inserted_id)

    @override
    def update(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update data in the collection_name collection based on a query.
        """
        if self.db_sources is None:
            raise Exception("Database connection is not established.")
        result = self.db_sources.get_collection(collection_name).update_many(query, {'$set': update})
        return result.modified_count

    @override
    def delete_instance(self, collection_name: str, query: Dict[str, Any]) -> int:
        """
        Delete data from the collection_name collection based on a query.
        """
        if self.db_sources is None:
            raise Exception("Database connection is not established.")
        result = self.db_sources.get_collection(collection_name).delete_many(query)
        return result.deleted_count

    @override
    def delete_collection(self, collection_name: str) -> int:
        """
        Delete all documents from the specified collection.
        Returns the number of documents deleted.
        """
        if self.db_sources is None:
            raise Exception("Database connection is not established.")

        # Using an empty query {} to match all documents in the collection
        result = self.db_sources[collection_name].delete_many({})
        return result.deleted_count

    # ----------------------------- Sources ----------------------------------
    @override
    def find_one(self, collection_name: str, key: str):
        if self.db_sources is None:
            raise Exception("Database connection is not established.")
        return self.db_sources.get_collection(collection_name).find_one({'key': key})

    @override
    def find_one_source(self, collection_name: str, key: str) -> Source:
        db_object = self.find_one(collection_name, key)
        if db_object is None:
            raise Exception(f"Collection {collection_name} and {key} does not exist.")
        return Source(
            key=db_object["key"],
            content=db_object["content"],
            filters=db_object["filters"],
            summary=db_object["summary"],
        )

    # ----------------------------- FAISS ------------------------------------
    @override
    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes) -> None:
        """
        Save the serialized FAISS index and metadata to MongoDB.

        Args:
            index_bytes (bytes): Serialized FAISS index.
            metadata_bytes (bytes): Serialized metadata (pickled).
        """
        # Use MongoDB's Binary wrapper to store raw bytes safely
        faiss_index_binary = Binary(index_bytes)
        metadata_binary = Binary(metadata_bytes)

        # Upsert the FAISS index document in the 'faiss_index' collection
        # An empty filter {} means we update the single (or first) document.
        # If no document exists, 'upsert=True' inserts a new one.
        self.db_faiss[CollectionName.FS.value].update_one(
            {},
            {"$set": {
                "faiss_index": faiss_index_binary,
                "metadata": metadata_binary
            }},
            upsert=True
        )

    @override
    def load_faiss_index(self) -> Optional[Tuple[bytes, bytes]]:
        """
        Load the FAISS index and metadata from MongoDB.

        Returns:
            Optional[Tuple[bytes, bytes]]: Tuple containing
                - index_bytes: Serialized FAISS index bytes
                - metadata_bytes: Serialized metadata bytes
            or None if no record is found.
        """
        # Fetch the single document from the 'faiss_index' collection
        record = self.db_faiss[CollectionName.FS.value].find_one({})

        # If no document found, return None
        if not record:
            return None

        # Extract the 'faiss_index' field and convert from BSON Binary to bytes
        index_bytes = bytes(record.get('faiss_index')) if record.get('faiss_index') else None
        # Extract the 'metadata' field similarly
        metadata_bytes = bytes(record.get("metadata")) if record.get("metadata") else None

        # If either part is missing, treat as no valid index stored
        if index_bytes is None or metadata_bytes is None:
            return None

        # Return both bytes objects as a tuple
        return index_bytes, metadata_bytes