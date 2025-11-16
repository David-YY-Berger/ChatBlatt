from bson import Binary
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from typing import Any, Dict, List, Optional, Tuple

from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.DataPipeline.DB.Collections import CollectionName, Collection
from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.General.Decorators import singleton
# from BackEnd.General.Logger import Logger
from typing_extensions import override

from BackEnd.DataObjects.SourceClasses import SourceContent
from BackEnd.DataObjects.SourceClasses.SourceContent import SourceContent

@singleton
class DBapiMongoDB(DBapiInterface):
    """
    A concrete implementation of DBapiInterface for MongoDB.
    """

    def __init__(self, connection_string: str = None):
        self.client: MongoClient | None = None
        self.dbs: Dict[str, any] = {}   # holds db_name -> MongoDatabase
        self.connection_string = connection_string
        # self.logger = Logger()

        if connection_string:
            self.connect(connection_string)

    def get_collection(self, collection: Collection):
        """
        Given a Collection object, return the Mongo collection object.
        """
        db = self.dbs.get(collection.db_name)
        if db is None:
            raise ValueError(f"Database {collection.db_name} not found")
        return db[collection.name]

    @override
    def connect(self, connection_string: str) -> None:
        """
        Connect to the MongoDB server and set up databases.
        """
        self.connection_string = connection_string
        self.client = MongoClient(connection_string, server_api=ServerApi('1'))

        try:
            self.client.admin.command('ping')
            # self.logger.debug("Connected to MongoDB")
        except Exception as e:
            # self.logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Failed to connect: {e}")

        # Initialize all DBs that exist in CollectionName
        for collection in CollectionName.all():
            if collection.db_name not in self.dbs:
                self.dbs[collection.db_name] = self.client.get_database(collection.db_name)

    @override
    def disconnect(self) -> None:
        """
        Close the MongoDB database connection.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.dbs.clear()  # reset all cached DB references
            # self.logger.debug("Disconnected from MongoDB")

    @override
    def execute_raw_query(self, query: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a MongoDB operation safely.
        Expected query format:
          {
            "collection": Collection,
            "operation": "find" | "update_one" | "update_many" | "delete_one" | "delete_many" | "insert_one",
            "filter": {...},      # for find/update/delete
            "update": {...},      # for update operations
            "document": {...}     # for insert operations
          }
        Returns:
          - For 'find': list of dicts
          - For update/delete/insert: operation result dict
        """
        collection_obj = query.get("collection")
        operation = query.get("operation", "find")
        collection = self.get_collection(collection_obj)

        if operation == "find":
            return list(collection.find(query.get("filter", {})))
        elif operation == "update_one":
            return collection.update_one(query["filter"], query["update"]).raw_result
        elif operation == "update_many":
            return collection.update_many(query["filter"], query["update"]).raw_result
        elif operation == "delete_one":
            return collection.delete_one(query["filter"]).raw_result
        elif operation == "delete_many":
            return collection.delete_many(query["filter"]).raw_result
        elif operation == "insert_one":
            return collection.insert_one(query["document"]).inserted_id
        elif operation == "insert_many":
            return collection.insert_many(query["documents"]).inserted_ids
        elif operation == "count_documents":
            return collection.count_documents(query.get("filter", {}))
        elif operation == "replace_one":
            return collection.replace_one(query["filter"], query["replacement"]).raw_result
        elif operation == "aggregate":
            return list(collection.aggregate(query["pipeline"]))
        elif operation == "find_one":
            return collection.find_one(query.get("filter", {}))
        elif operation == "distinct":
            return collection.distinct(query["field"], query.get("filter", {}))
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    @override
    def execute_query_with_collection(self, query: Dict[str, Any], collection: Collection):
        """
        Wrapper for execute_raw_query that accepts a collection object.
        It adds the collection to the query dict and calls execute_raw_query.
        """
        # Make a copy of the query to avoid mutating the caller's dict
        query_with_collection = query.copy()
        query_with_collection["collection"] = collection  # use the passed Collection object
        return self.execute_raw_query(query_with_collection)

    @override
    def insert(self, collection: Collection, data: Dict[str, Any]) -> str:
        """
        Insert data into the specified collection.
        """
        if not self.client:
            raise Exception("Database connection is not established.")

        get_collection = self.get_collection(collection)
        result = get_collection.insert_one(data)
        return str(result.inserted_id)

    @override
    def update(self, collection: Collection, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update documents in the specified collection based on a query.
        """
        if not self.client:
            raise Exception("Database connection is not established.")

        result = self.get_collection(collection).update_many(query, {"$set": update})
        return result.modified_count

    @override
    def delete_instance(self, collection: Collection, query: Dict[str, Any]) -> int:
        """
        Delete documents from the specified collection based on a query.
        """
        if not self.client:
            raise Exception("Database connection is not established.")

        result = self.get_collection(collection).delete_many(query)
        return result.deleted_count

    @override
    def delete_collection(self, collection: Collection) -> int:
        """
        Delete all documents from the specified collection.
        Returns the number of documents deleted.
        """
        if not self.client:
            raise Exception("Database connection is not established.")

        result = self.get_collection(collection).delete_many({})
        return result.deleted_count

    # ----------------------------- Source Content ----------------------------------
    @override
    def find_one(self, collection: Collection, key: str) -> Dict[str, Any] | None:
        """
        Find a single document in the given collection by key.
        """
        if not self.client:
            raise Exception("Database connection is not established.")
        return self.get_collection(collection).find_one({"key": key})

    @override
    def find_one_source_content(self, collection: Collection, key: str) -> SourceContent:
        """
        Find a single document and return it as a Source object.
        """
        db_object = self.find_one(collection, key)
        if db_object is None:
            raise Exception(f"Document with key '{key}' not found in collection {collection.name}.")

        return SourceContent(
            key=db_object["key"],
            content=db_object["content"]
        )

    @override
    def get_all_source_contents(self, collection: Collection) -> List[SourceContent]:
        """
        Retrieve all documents from the given collection and return them as SourceContent objects.
        """
        if not self.client:
            raise Exception("Database connection is not established.")

        docs = self.get_collection(collection).find({})
        return [
            SourceContent(key=doc["key"], content=doc["content"])
            for doc in docs
            if "key" in doc and "content" in doc
        ]

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
        self.get_collection(CollectionName.FS).update_one(
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
        # Use the Collection object for FAISS
        faiss_collection = CollectionName.FS
        record = self.get_collection(faiss_collection).find_one({})

        if not record:
            return None

        # Convert fields from BSON Binary to bytes
        index_bytes = bytes(record.get("faiss_index")) if record.get("faiss_index") else None
        metadata_bytes = bytes(record.get("metadata")) if record.get("metadata") else None

        if index_bytes is None or metadata_bytes is None:
            return None

        return index_bytes, metadata_bytes

    # ----------------------------- Source Metadata (Lmm) ------------------------------------
    @override
    def is_src_metadata_exist(self, key: str) -> bool:
        return True

    @override
    def insert_source_metadata(self, src_metadata:SourceMetadata) -> str:
        pass

    @override
    def update_source_metadata(self, src_metadata:SourceMetadata) -> str:
        pass