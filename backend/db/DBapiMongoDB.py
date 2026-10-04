import functools
import gzip
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

import bson
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from typing_extensions import override

from backend.common.Decorators import singleton
from backend.db.Collections import CollectionObjs, Collection
from backend.db.DBConstants import DBFields
from backend.db.DBapiInterface import DBapiInterface
from backend.db.mongo_parts.entity_mixin import EntityMongoMixin
from backend.db.mongo_parts.genealogy_mixin import GenealogyMongoMixin
from backend.db.mongo_parts.relationship_mixin import RelationshipMongoMixin
from backend.db.mongo_parts.select_option_mixin import SelectOptionMongoMixin
from backend.db.mongo_parts.similarity_index_mixin import SimilarityIndexMongoMixin
from backend.db.mongo_parts.source_content_mixin import SourceContentMongoMixin
from backend.db.mongo_parts.source_metadata_mixin import SourceMetadataMongoMixin

T = TypeVar("T")

# pymongo Collection operations that take a `session` and may run inside a transaction.
_TRANSACTIONAL_COLLECTION_METHODS = frozenset({
    "find", "find_one", "find_one_and_delete", "find_one_and_replace", "find_one_and_update",
    "insert_one", "insert_many", "update_one", "update_many", "replace_one",
    "delete_one", "delete_many", "bulk_write", "count_documents", "distinct", "aggregate",
})


class _SessionBoundCollection:
    """A pymongo Collection whose operations all run in the given session - and so in its transaction."""

    def __init__(self, collection, session):
        self._collection = collection
        self._session = session

    def __getattr__(self, name):
        attr = getattr(self._collection, name)
        if name in _TRANSACTIONAL_COLLECTION_METHODS:
            return functools.partial(attr, session=self._session)
        return attr


@singleton
class DBapiMongoDB(
    SourceContentMongoMixin,
    SimilarityIndexMongoMixin,
    EntityMongoMixin,
    RelationshipMongoMixin,
    SourceMetadataMongoMixin,
    SelectOptionMongoMixin,
    GenealogyMongoMixin,
    DBapiInterface,
):
    """Mongo implementation composed from per-domain mixins."""

    def __init__(self, connection_string: str = None):
        self.client: MongoClient | None = None
        self.dbs: Dict[str, Any] = {}
        self.connection_string = connection_string
        self._transaction = threading.local()  # .session: the session of this thread's active transaction

        if connection_string:
            self.connect(connection_string)

    def get_collection(self, collection: Collection):
        db = self.dbs.get(collection.db_name)
        if db is None:
            raise ValueError(f"Database {collection.db_name} not found")
        mongo_collection = db[collection.name]
        session = getattr(self._transaction, "session", None)
        return mongo_collection if session is None else _SessionBoundCollection(mongo_collection, session)

    @override
    def run_in_transaction(self, callback: Callable[[], T]) -> T:
        """
        Runs callback() in one MongoDB transaction and returns its result. Every DB operation
        made through this object during the call (from this thread, reads included) joins the
        transaction - reads see its uncommitted writes - and all its writes are committed
        together when callback returns, or rolled back if it raises.
        On a transient error (e.g. a write conflict) pymongo rolls back and re-runs callback,
        so callback must be safe to repeat.
        MongoDB aborts transactions running longer than transactionLifetimeLimitSeconds
        (60 seconds by default), so keep each one short.
        """
        if getattr(self._transaction, "session", None) is not None:
            raise RuntimeError("A transaction is already running - nested transactions are not supported.")

        def run_bound_to(session):
            self._transaction.session = session
            try:
                return callback()
            finally:
                self._transaction.session = None

        with self.client.start_session() as session:
            return session.with_transaction(run_bound_to)

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

        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """
        Create indexes on first connect (idempotent — safe to call repeatedly).

        Entities collection:
          - Compound (entityType, display_en_name): covers get_enumbers_by_value and
            all name+type existence queries during population.
          - Single (key): fast key-based lookups everywhere.

        SourceMetadata collection:
          - Multikey (entity_keys): MongoDB indexes each array element individually,
            making "find all SourceMetadata containing entity key X" an index scan
            instead of a full collection scan.
          - Multikey (rel_keys): same benefit, for "find all SourceMetadata
            containing relationship key X" (used e.g. when re-pointing/cleaning up
            relationships during entity merges).
        """
        from pymongo import ASCENDING

        entities = self.get_collection(CollectionObjs.ENTITIES)
        entities.create_index(
            [(DBFields.ENTITY_TYPE, ASCENDING), (DBFields.DISPLAY_EN_NAME, ASCENDING)],
            name="idx_entity_type_name",
        )
        entities.create_index(
            [(DBFields.KEY, ASCENDING)],
            name="idx_entity_key",
            unique=True,
            sparse=True,  # sparse: documents without 'key' (during insert) are excluded
        )

        src_metadata = self.get_collection(CollectionObjs.SRC_METADATA)
        src_metadata.create_index(
            [(DBFields.ENTITY_KEYS, ASCENDING)],
            name="idx_src_metadata_entity_keys",
        )
        src_metadata.create_index(
            [(DBFields.REL_KEYS, ASCENDING)],
            name="idx_src_metadata_rel_keys",
        )

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
