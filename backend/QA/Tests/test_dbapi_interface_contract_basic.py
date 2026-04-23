import unittest
import inspect

from backend.db.Collections import CollectionObjs
from backend.db.DBapiInterface import DBapiInterface
from backend.models.Enums import SourceType
from backend.models.SourceClasses.SourceMetadata import SourceMetadata


class InMemoryDBapi(DBapiInterface):
    def __init__(self):
        self.connected = False
        self.storage = {}
        self.faiss = None

    def connect(self, connection_string: str) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def execute_raw_query(self, query):
        return query

    def execute_query_with_collection(self, query, collection):
        query = dict(query)
        query["collection"] = collection.name
        return query

    def insert(self, collection, data):
        self.storage[(collection.name, data["key"])] = data
        return data["key"]

    def update(self, collection, query, update):
        key = query.get("key")
        rec = self.storage.get((collection.name, key))
        if not rec:
            return 0
        rec.update(update)
        return 1

    def find_one(self, collection, key: str):
        return self.storage.get((collection.name, key))

    def delete_instance(self, collection, query):
        key = query.get("key")
        return 1 if self.storage.pop((collection.name, key), None) else 0

    def delete_collection(self, collection):
        keys = [k for k in self.storage if k[0] == collection.name]
        for key in keys:
            self.storage.pop(key)
        return len(keys)

    def _find_one_source_content_by_col(self, collection, key: str):
        raise NotImplementedError

    def get_all_src_contents_of_collection(self, collection):
        return []

    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes) -> None:
        self.faiss = (index_bytes, metadata_bytes)

    def load_faiss_index(self):
        return self.faiss

    def is_entity_exists(self, key: str) -> bool:
        return False

    def insert_entity(self, entity):
        return entity.key

    def update_entity(self, entity):
        return 1

    def get_entity_by_key(self, key: str):
        return None

    def get_entities_by_keys(self, keys):
        return []

    def get_entities_by_type(self, entity_type):
        return []

    def get_all_entities(self):
        return []

    def search_entities_by_name(self, name: str, entity_type=None):
        return []

    def insert_entities_bulk(self, entities):
        return len(entities)

    def upsert_entities_bulk(self, entities):
        return (0, 0)

    def is_rel_exists(self, key: str) -> bool:
        return False

    def insert_rel(self, rel):
        return rel.key

    def update_rel(self, rel):
        return 1

    def get_rel_by_key(self, key: str):
        return None

    def get_rels_by_keys(self, keys):
        return []

    def get_rels_for_entity(self, entity_key: str):
        return []

    def get_all_rels(self):
        return []

    def insert_rels_bulk(self, rels):
        return len(rels)

    def upsert_rels_bulk(self, rels):
        return (0, 0)

    def is_src_metadata_exists(self, key: str) -> bool:
        return False

    def insert_source_metadata(self, src_metadata: SourceMetadata) -> str:
        return src_metadata.key

    def update_source_metadata(self, src_metadata: SourceMetadata) -> int:
        return 1

    def get_source_metadata_by_key(self, key: str):
        return None

    def get_all_source_metadata(self):
        return []


class DBapiInterfaceContractTests(unittest.TestCase):
    def test_interface_is_abstract(self):
        self.assertTrue(inspect.isabstract(DBapiInterface))

    def test_concrete_implementation_exercises_cross_mixin_defaults(self):
        db = InMemoryDBapi()

        db.connect("unused")
        self.assertTrue(db.connected)

        inserted_key = db.insert(CollectionObjs.TN, {"key": "TN_Genesis_1_1", "content": ["en", "he", ""]})
        self.assertEqual(inserted_key, "TN_Genesis_1_1")
        self.assertTrue(db.exists(CollectionObjs.TN, "TN_Genesis_1_1"))

        db.save_faiss_index(b"idx", b"meta")
        self.assertEqual(db.load_faiss_index(), (b"idx", b"meta"))

        metadata = SourceMetadata(source_type=SourceType.TN)
        metadata.key = "TN_Genesis_1_1"
        self.assertEqual(db.upsert_source_metadata(metadata), metadata.key)

        db.disconnect()
        self.assertFalse(db.connected)


if __name__ == "__main__":
    unittest.main()



