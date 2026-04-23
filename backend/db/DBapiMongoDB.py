import gzip
from datetime import datetime

import bson
from bson import Binary
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from typing import Any, Dict, List, Optional, Tuple

from backend.models.EntityObjects.Entity import Entity
from backend.models.Rel import Rel
from backend.models.Enums import EntityType
from backend.models.SourceClasses.SourceMetadata import SourceMetadata
from backend.db.Collections import CollectionObjs, Collection
from backend.db.DBConstants import DBFields, DBOperators
from backend.db.DBapiInterface import DBapiInterface
from backend.common.Decorators import singleton
# from backend.common.Logger import Logger
from typing_extensions import override

from backend.models.SourceClasses import SourceContent
from backend.models.SourceClasses.SourceContent import SourceContent

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
        for collection in CollectionObjs.all():
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
            self.dbs.clear()  # reset all cached db references
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
    def _find_one_source_content_by_col(self, collection: Collection, key: str) -> SourceContent:
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
    def get_all_src_contents_of_collection(self, collection: Collection) -> List[SourceContent]:
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
        self.get_collection(CollectionObjs.FS).update_one(
            {},
            {DBOperators.SET: {
                DBFields.FAISS_INDEX: faiss_index_binary,
                DBFields.METADATA: metadata_binary
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
        faiss_collection = CollectionObjs.FS
        record = self.get_collection(faiss_collection).find_one({})

        if not record:
            return None

        # Convert fields from BSON Binary to bytes
        index_bytes = bytes(record.get(DBFields.FAISS_INDEX)) if record.get(DBFields.FAISS_INDEX) else None
        metadata_bytes = bytes(record.get(DBFields.METADATA)) if record.get(DBFields.METADATA) else None

        if index_bytes is None or metadata_bytes is None:
            return None

        return index_bytes, metadata_bytes

    # ----------------------------- Entity ------------------------------------
    @override
    def is_entity_exists(self, key: str) -> bool:
        """Check if an entity with the given key exists."""
        return self.get_collection(CollectionObjs.ENTITIES).find_one({DBFields.KEY: key}) is not None

    @override
    def insert_entity(self, entity: Entity) -> str:
        """Insert a new entity. Returns the inserted document ID."""
        data = entity.to_db_dict()
        data[DBFields.ENTITY_TYPE] = entity.entityType.value
        result = self.get_collection(CollectionObjs.ENTITIES).insert_one(data)
        return str(result.inserted_id)

    @override
    def update_entity(self, entity: Entity) -> int:
        """Update an existing entity by key. Returns modified count."""
        data = entity.to_db_dict()
        data[DBFields.ENTITY_TYPE] = entity.entityType.value
        key = data.pop(DBFields.KEY)
        result = self.get_collection(CollectionObjs.ENTITIES).update_one(
            {DBFields.KEY: key},
            {DBOperators.SET: data}
        )
        return result.modified_count

    @override
    def get_entity_by_key(self, key: str) -> Optional[Entity]:
        """Retrieve an entity by its key."""
        doc = self.get_collection(CollectionObjs.ENTITIES).find_one({DBFields.KEY: key})
        if doc is None:
            return None
        return self._doc_to_entity(doc)

    @override
    def get_entities_by_keys(self, keys: List[str]) -> List[Entity]:
        """Retrieve multiple entities by their keys."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find({DBFields.KEY: {DBOperators.IN: keys}})
        return [self._doc_to_entity(doc) for doc in docs]

    @override
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Retrieve all entities of a specific type."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find({DBFields.ENTITY_TYPE: entity_type.value})
        return [self._doc_to_entity(doc) for doc in docs]

    @override
    def get_all_entities(self) -> List[Entity]:
        """Retrieve all entities."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find({})
        return [self._doc_to_entity(doc) for doc in docs]

    @override
    def search_entities_by_name(self, name: str, entity_type: Optional[EntityType] = None) -> List[Entity]:
        """Search entities by name (searches all name fields)."""
        regex_pattern = {DBOperators.REGEX: name, DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE}
        name_query = {
            DBOperators.OR: [
                {DBFields.DISPLAY_EN_NAME: regex_pattern},
                {DBFields.DISPLAY_HEB_NAME: regex_pattern},
                {DBFields.ALL_EN_NAMES: regex_pattern},
                {DBFields.ALL_HEB_NAMES: regex_pattern},
            ]
        }
        if entity_type:
            query = {DBOperators.AND: [name_query, {DBFields.ENTITY_TYPE: entity_type.value}]}
        else:
            query = name_query

        docs = self.get_collection(CollectionObjs.ENTITIES).find(query)
        return [self._doc_to_entity(doc) for doc in docs]

    @override
    def insert_entities_bulk(self, entities: List[Entity]) -> int:
        """Bulk insert multiple entities. Returns number of inserted documents."""
        if not entities:
            return 0
        docs = []
        for entity in entities:
            data = entity.to_db_dict()
            data[DBFields.ENTITY_TYPE] = entity.entityType.value
            docs.append(data)
        result = self.get_collection(CollectionObjs.ENTITIES).insert_many(docs)
        return len(result.inserted_ids)

    @override
    def upsert_entities_bulk(self, entities: List[Entity]) -> Tuple[int, int]:
        """Bulk upsert multiple entities. Returns (inserted_count, updated_count)."""
        from pymongo import UpdateOne

        if not entities:
            return (0, 0)

        operations = []
        for entity in entities:
            data = entity.to_db_dict()
            data[DBFields.ENTITY_TYPE] = entity.entityType.value
            operations.append(
                UpdateOne(
                    {DBFields.KEY: entity.key},
                    {DBOperators.SET: data},
                    upsert=True
                )
            )

        result = self.get_collection(CollectionObjs.ENTITIES).bulk_write(operations)
        return (result.upserted_count, result.modified_count)

    def _doc_to_entity(self, doc: Dict[str, Any]) -> Entity:
        """Convert a MongoDB document to the appropriate Entity subclass."""
        from backend.models.EntityObjects.EPerson import EPerson
        from backend.models.EntityObjects.EPlace import EPlace
        from backend.models.EntityObjects.ENation import ENation
        from backend.models.EntityObjects.ESymbol import ESymbol
        from backend.models.EntityObjects.ETribeOfIsrael import ETribeOfIsrael
        from backend.models.EntityObjects.ENumber import ENumber
        from backend.models.EntityObjects.EAnimal import EAnimal
        from backend.models.EntityObjects.EFood import EFood
        from backend.models.EntityObjects.EPlant import EPlant

        # Remove MongoDB _id field
        doc = {k: v for k, v in doc.items() if k != '_id'}

        # Get entity type and convert from stored value
        entity_type_value = doc.get(DBFields.ENTITY_TYPE)
        entity_type = EntityType(entity_type_value)

        # Map EntityType to the correct subclass
        entity_class_map = {
            EntityType.EPerson: EPerson,
            EntityType.EPlace: EPlace,
            EntityType.ENation: ENation,
            EntityType.ESymbol: ESymbol,
            EntityType.ETribeOfIsrael: ETribeOfIsrael,
            EntityType.ENumber: ENumber,
            EntityType.EAnimal: EAnimal,
            EntityType.EFood: EFood,
            EntityType.EPlant: EPlant,
        }

        entity_class = entity_class_map.get(entity_type, Entity)
        return entity_class.model_validate(doc)

    # ----------------------------- Relationship ------------------------------------
    @override
    def is_rel_exists(self, key: str) -> bool:
        """Check if a relationship with the given key exists."""
        return self.get_collection(CollectionObjs.RELATIONS).find_one({DBFields.KEY: key}) is not None

    @override
    def insert_rel(self, rel: Rel) -> str:
        """Insert a new relationship. Returns the inserted document ID."""
        data = rel.to_db_dict()
        data[DBFields.REL_TYPE] = rel.rel_type.value
        result = self.get_collection(CollectionObjs.RELATIONS).insert_one(data)
        return str(result.inserted_id)

    @override
    def update_rel(self, rel: Rel) -> int:
        """Update an existing relationship by key. Returns modified count."""
        data = rel.to_db_dict()
        data[DBFields.REL_TYPE] = rel.rel_type.value
        key = data.pop(DBFields.KEY)
        result = self.get_collection(CollectionObjs.RELATIONS).update_one(
            {DBFields.KEY: key},
            {DBOperators.SET: data}
        )
        return result.modified_count

    @override
    def get_rel_by_key(self, key: str) -> Optional[Rel]:
        """Retrieve a relationship by its key."""
        doc = self.get_collection(CollectionObjs.RELATIONS).find_one({DBFields.KEY: key})
        if doc is None:
            return None
        return self._doc_to_rel(doc)

    @override
    def get_rels_by_keys(self, keys: List[str]) -> List[Rel]:
        """Retrieve multiple relationships by their keys."""
        docs = self.get_collection(CollectionObjs.RELATIONS).find({DBFields.KEY: {DBOperators.IN: keys}})
        return [self._doc_to_rel(doc) for doc in docs]

    @override
    def get_rels_for_entity(self, entity_key: str) -> List[Rel]:
        """Retrieve all relationships where the entity is term1 or term2."""
        docs = self.get_collection(CollectionObjs.RELATIONS).find({
            DBOperators.OR: [
                {DBFields.TERM1: entity_key},
                {DBFields.TERM2: entity_key}
            ]
        })
        return [self._doc_to_rel(doc) for doc in docs]

    @override
    def get_all_rels(self) -> List[Rel]:
        """Retrieve all relationships."""
        docs = self.get_collection(CollectionObjs.RELATIONS).find({})
        return [self._doc_to_rel(doc) for doc in docs]

    @override
    def insert_rels_bulk(self, rels: List[Rel]) -> int:
        """Bulk insert multiple relationships. Returns number of inserted documents."""
        if not rels:
            return 0
        docs = []
        for rel in rels:
            data = rel.to_db_dict()
            data[DBFields.REL_TYPE] = rel.rel_type.value
            docs.append(data)
        result = self.get_collection(CollectionObjs.RELATIONS).insert_many(docs)
        return len(result.inserted_ids)

    @override
    def upsert_rels_bulk(self, rels: List[Rel]) -> Tuple[int, int]:
        """Bulk upsert multiple relationships. Returns (inserted_count, updated_count)."""
        from pymongo import UpdateOne

        if not rels:
            return (0, 0)

        operations = []
        for rel in rels:
            data = rel.to_db_dict()
            data[DBFields.REL_TYPE] = rel.rel_type.value
            operations.append(
                UpdateOne(
                    {DBFields.KEY: rel.key},
                    {DBOperators.SET: data},
                    upsert=True
                )
            )

        result = self.get_collection(CollectionObjs.RELATIONS).bulk_write(operations)
        return (result.upserted_count, result.modified_count)

    def _doc_to_rel(self, doc: Dict[str, Any]) -> Rel:
        """Convert a MongoDB document to a Rel object."""
        from backend.models.Enums import RelType

        # Remove MongoDB _id field
        doc = {k: v for k, v in doc.items() if k != '_id'}

        # Convert stored rel_type value back to enum
        rel_type_value = doc.get(DBFields.REL_TYPE)
        doc[DBFields.REL_TYPE] = RelType(rel_type_value)

        return Rel.model_validate(doc)

    # ----------------------------- Source Metadata ------------------------------------
    @override
    def is_src_metadata_exists(self, key: str) -> bool:
        """Check if source metadata with the given key exists."""
        return self.get_collection(CollectionObjs.SRC_METADATA).find_one({DBFields.KEY: key}) is not None

    @override
    def insert_source_metadata(self, src_metadata: SourceMetadata) -> str:
        """Insert new source metadata. Returns the inserted document ID."""
        data = self._src_metadata_to_doc(src_metadata)
        result = self.get_collection(CollectionObjs.SRC_METADATA).insert_one(data)
        return str(result.inserted_id)

    @override
    def update_source_metadata(self, src_metadata: SourceMetadata) -> int:
        """Update existing source metadata by key. Returns modified count."""
        data = self._src_metadata_to_doc(src_metadata)
        key = data.pop(DBFields.KEY)
        result = self.get_collection(CollectionObjs.SRC_METADATA).update_one(
            {DBFields.KEY: key},
            {DBOperators.SET: data}
        )
        return result.modified_count

    @override
    def get_source_metadata_by_key(self, key: str) -> Optional[SourceMetadata]:
        """Retrieve source metadata by its key."""
        doc = self.get_collection(CollectionObjs.SRC_METADATA).find_one({DBFields.KEY: key})
        if doc is None:
            return None
        return self._doc_to_src_metadata(doc)

    @override
    def get_all_source_metadata(self) -> List[SourceMetadata]:
        """Retrieve all source metadata."""
        docs = self.get_collection(CollectionObjs.SRC_METADATA).find({})
        return [self._doc_to_src_metadata(doc) for doc in docs]

    def _src_metadata_to_doc(self, src_metadata: SourceMetadata) -> Dict[str, Any]:
        """Convert SourceMetadata to a MongoDB document."""
        return {
            DBFields.KEY: src_metadata.key,
            DBFields.SOURCE_TYPE: src_metadata.source_type.value,
            DBFields.SUMMARY_EN: src_metadata.summary_en,
            DBFields.SUMMARY_HEB: src_metadata.summary_heb,
            DBFields.PASSAGE_TYPES: [pt.value for pt in src_metadata.passage_types],
            DBFields.ENTITY_KEYS: list(src_metadata.entity_keys),
            DBFields.REL_KEYS: list(src_metadata.rel_keys),
        }

    def _doc_to_src_metadata(self, doc: Dict[str, Any]) -> SourceMetadata:
        """Convert a MongoDB document to SourceMetadata."""
        from backend.models.Enums import SourceType, PassageType

        # SourceMetadata is a dataclass that inherits from SourceClass
        # We need to construct it properly
        sm = SourceMetadata(
            source_type=SourceType(doc[DBFields.SOURCE_TYPE]),
        )
        # Set key from parent class
        sm.key = doc[DBFields.KEY]
        sm.summary_en = doc.get(DBFields.SUMMARY_EN)
        sm.summary_heb = doc.get(DBFields.SUMMARY_HEB)
        sm.passage_types = [PassageType(pt) for pt in doc.get(DBFields.PASSAGE_TYPES, [])]
        sm.entity_keys = set(doc.get(DBFields.ENTITY_KEYS, []))
        sm.rel_keys = set(doc.get(DBFields.REL_KEYS, []))
        return sm

    # ----------------------------- db Maintainance ------------------------------------
    def get_backup_mongo_dump(self, output_filename: str = None):
        """
        Iterates through all initialized databases, fetches all documents,
        and saves them into a compressed BSON archive.
        """
        if not self.client:
            raise Exception("Database connection is not established.")

        # Default filename with timestamp
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"atlas_backup_{timestamp}.bson.gz"

        with gzip.open(output_filename, "wb") as f:
            for db_name, db_obj in self.dbs.items():
                for collection_name in db_obj.list_collection_names():
                    collection = db_obj[collection_name]

                    for doc in collection.find():
                        # We store the db and coll info in a wrapper to make
                        # restoration easier later
                        wrapper = {
                            "db": db_name,
                            "coll": collection_name,
                            "data": doc
                        }
                        f.write(bson.BSON.encode(wrapper))

        return output_filename
