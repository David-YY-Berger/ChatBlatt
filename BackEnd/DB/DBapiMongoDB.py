from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from typing import Any, Dict, List

from BackEnd.DB.DBapiInterface import DBapiInterface
from BackEnd.General.Logger import Logger
from BackEnd.Objects.SourceClasses import Source


class DBapiMongoDB(DBapiInterface):
    """
    A concrete implementation of DBapiInterface for MongoDB.
    """

    def __init__(self, connection_string: str = None):
        self.collection = None
        self.client = None
        self.db = None
        self.connection_string = connection_string
        self.logger = Logger()

        if connection_string:
            self.connect(connection_string)

    def connect(self, connection_string: str) -> None:
        """
        Connect to the MongoDB database.
        """
        self.connection_string = connection_string
        self.client = MongoClient(connection_string, server_api=ServerApi('1'))
        try:
            self.client.admin.command('ping') #fails here <
            self.logger.debug("Connected to the database")
        except Exception as e:
            print(f"Failed to connect: {e}")
            raise ConnectionError(f"Failed to connect: {e}")


        self.db = self.client.get_database('test_db')

        # Create the collection 'en-sources' if not exists
        self.collection = self.db.get_collection('en-sources')


    def disconnect(self) -> None:
        """
        Close the MongoDB database connection.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

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

    def insert(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Insert data into the 'en-sources' collection.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")
        result = self.collection.insert_one(data)
        return str(result.inserted_id)


    def update(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update data in the 'en-sources' collection based on a query.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")
        result = self.collection.update_many(query, {'$set': update})
        return result.modified_count

    def delete(self, collection: str, query: Dict[str, Any]) -> int:
        """
        Delete data from the 'en-sources' collection based on a query.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")
        result = self.collection.delete_many(query)
        return result.deleted_count

    def delete_all(self, collection: str) -> int:
        """
        Delete all documents from the specified collection.
        Returns the number of documents deleted.
        """
        if self.db is None:
            raise Exception("Database connection is not established.")

        # Using an empty query {} to match all documents in the collection
        result = self.db[collection].delete_many({})
        return result.deleted_count