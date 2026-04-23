import gzip
from datetime import datetime
from typing import Any, Dict, List, Optional

import bson
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from typing_extensions import override

from backend.common.Decorators import singleton
from backend.db.Collections import CollectionObjs, Collection
from backend.db.DBapiInterface import DBapiInterface
from backend.db.mongo_parts.entity_mixin import EntityMongoMixin
from backend.db.mongo_parts.faiss_mixin import FaissMongoMixin
from backend.db.mongo_parts.relationship_mixin import RelationshipMongoMixin
from backend.db.mongo_parts.source_content_mixin import SourceContentMongoMixin
from backend.db.mongo_parts.source_metadata_mixin import SourceMetadataMongoMixin


@singleton
class DBapiMongoDB(
    SourceContentMongoMixin,
    FaissMongoMixin,
    EntityMongoMixin,
    RelationshipMongoMixin,
    SourceMetadataMongoMixin,
    DBapiInterface,
):
    """Mongo implementation composed from per-domain mixins."""

    def __init__(self, connection_string: str = None):
        self.client: MongoClient | None = None
        self.dbs: Dict[str, Any] = {}
        self.connection_string = connection_string

        if connection_string:
            self.connect(connection_string)

    def get_collection(self, collection: Collection):
        db = self.dbs.get(collection.db_name)
        if db is None:
            raise ValueError(f"Database {collection.db_name} not found")
        return db[collection.name]

    @override
    def connect(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self.client = MongoClient(connection_string, server_api=ServerApi("1"))

        try:
            self.client.admin.command("ping")
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

        for collection in CollectionObjs.all():
            if collection.db_name not in self.dbs:
                self.dbs[collection.db_name] = self.client.get_database(collection.db_name)

    @override
    def disconnect(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
            self.dbs.clear()

    @override
    def execute_raw_query(self, query: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
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
        query_with_collection = query.copy()
        query_with_collection["collection"] = collection
        return self.execute_raw_query(query_with_collection)

    @override
    def insert(self, collection: Collection, data: Dict[str, Any]) -> str:
        if not self.client:
            raise Exception("Database connection is not established.")

        result = self.get_collection(collection).insert_one(data)
        return str(result.inserted_id)

    @override
    def update(self, collection: Collection, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        if not self.client:
            raise Exception("Database connection is not established.")

        result = self.get_collection(collection).update_many(query, {"$set": update})
        return result.modified_count

    @override
    def delete_instance(self, collection: Collection, query: Dict[str, Any]) -> int:
        if not self.client:
            raise Exception("Database connection is not established.")

        result = self.get_collection(collection).delete_many(query)
        return result.deleted_count

    @override
    def delete_collection(self, collection: Collection) -> int:
        if not self.client:
            raise Exception("Database connection is not established.")

        result = self.get_collection(collection).delete_many({})
        return result.deleted_count

    def get_backup_mongo_dump(self, output_filename: str = None):
        if not self.client:
            raise Exception("Database connection is not established.")

        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"atlas_backup_{timestamp}.bson.gz"

        with gzip.open(output_filename, "wb") as f:
            for db_name, db_obj in self.dbs.items():
                for collection_name in db_obj.list_collection_names():
                    collection = db_obj[collection_name]
                    for doc in collection.find():
                        wrapper = {
                            "db": db_name,
                            "coll": collection_name,
                            "data": doc,
                        }
                        f.write(bson.BSON.encode(wrapper))

        return output_filename
