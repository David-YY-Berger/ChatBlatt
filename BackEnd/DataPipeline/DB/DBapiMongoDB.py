from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from typing import Any, Dict, List

from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.General.Logger import Logger
from typing_extensions import override


class DBapiMongoDB(DBapiInterface):
    """
    A concrete implementation of DBapiInterface for MongoDB.
    """

    def __init__(self, connection_string: str = None):

        self.client = None
        self.db = None
        self.connection_string = connection_string
        self.logger = Logger()

        self.database_name = 'Sources'

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


        self.db = self.client.get_database(self.database_name)

    @override
    def disconnect(self) -> None:
        """
        Close the MongoDB database connection.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    @override
    def execute_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query on a MongoDB collection and return results.
        """
        collection_name = query.get('collection')
        query_filter = query.get('filter', {})
        if collection_name:
            collection = self.db[collection_name]
            return list(collection.find(query_filter))
        return []

    @override
    def insert(self, collection_name: str, data: Dict[str, Any]) -> str:
        """
        Insert data into the collection_name collection.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")
        result = self.db.get_collection(collection_name).insert_one(data)
        return str(result.inserted_id)

    @override
    def update(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update data in the collection_name collection based on a query.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")
        result = self.db.get_collection(collection_name).update_many(query, {'$set': update})
        return result.modified_count

    @override
    def delete_instance(self, collection_name: str, query: Dict[str, Any]) -> int:
        """
        Delete data from the collection_name collection based on a query.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")
        result = self.db.get_collection(collection_name).delete_many(query)
        return result.deleted_count

    @override
    def delete_collection(self, collection_name: str) -> int:
        """
        Delete all documents from the specified collection.
        Returns the number of documents deleted.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")

        # Using an empty query {} to match all documents in the collection
        result = self.db[collection_name].delete_many({})
        return result.deleted_count
