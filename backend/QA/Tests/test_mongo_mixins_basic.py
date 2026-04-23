import unittest
from dataclasses import dataclass

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.db.mongo_parts.entity_mixin import EntityMongoMixin
from backend.db.mongo_parts.faiss_mixin import FaissMongoMixin
from backend.db.mongo_parts.relationship_mixin import RelationshipMongoMixin
from backend.db.mongo_parts.source_content_mixin import SourceContentMongoMixin
from backend.db.mongo_parts.source_metadata_mixin import SourceMetadataMongoMixin
from backend.models.EntityObjects.EPlant import EPlant
from backend.models.Enums import PassageType, RelType, SourceType
from backend.models.Rel import Rel
from backend.models.SourceClasses.SourceMetadata import SourceMetadata


@dataclass
class _SimpleResult:
    inserted_id: str = "id1"
    inserted_ids: list | None = None
    modified_count: int = 0
    upserted_count: int = 0
    raw_result: dict | None = None


class FakeCollection:
    def __init__(self):
        self.find_one_result = None
        self.find_result = []
        self.last_find_query = None
        self.last_update_one = None
        self.last_insert_one_doc = None
        self.last_insert_many_docs = None
        self.bulk_write_result = _SimpleResult(upserted_count=2, modified_count=3)

    def find_one(self, query):
        self.last_find_query = query
        return self.find_one_result

    def find(self, query):
        self.last_find_query = query
        return list(self.find_result)

    def insert_one(self, doc):
        self.last_insert_one_doc = doc
        return _SimpleResult(inserted_id="id42")

    def update_one(self, query, update, upsert=False):
        self.last_update_one = (query, update, upsert)
        return _SimpleResult(modified_count=1)

    def insert_many(self, docs):
        self.last_insert_many_docs = docs
        return _SimpleResult(inserted_ids=["a", "b"])

    def bulk_write(self, operations):
        self.last_bulk_operations = operations
        return self.bulk_write_result


class DummyEntityMongo(EntityMongoMixin):
    def __init__(self):
        self.collections = {CollectionObjs.ENTITIES: FakeCollection()}

    def get_collection(self, collection):
        return self.collections[collection]


class DummyRelationshipMongo(RelationshipMongoMixin):
    def __init__(self):
        self.collections = {CollectionObjs.RELATIONS: FakeCollection()}

    def get_collection(self, collection):
        return self.collections[collection]


class DummyFaissMongo(FaissMongoMixin):
    def __init__(self):
        self.collections = {CollectionObjs.FS: FakeCollection()}

    def get_collection(self, collection):
        return self.collections[collection]


class DummySourceContentMongo(SourceContentMongoMixin):
    def __init__(self, has_client=True):
        self.client = object() if has_client else None
        self.collections = {CollectionObjs.BT: FakeCollection()}

    def get_collection(self, collection):
        return self.collections[collection]


class DummySourceMetadataMongo(SourceMetadataMongoMixin):
    def __init__(self):
        self.collections = {CollectionObjs.SRC_METADATA: FakeCollection()}

    def get_collection(self, collection):
        return self.collections[collection]


class MongoMixinsBasicTests(unittest.TestCase):
    def test_entity_insert_sets_entity_type_value(self):
        mixin = DummyEntityMongo()
        entity = EPlant(
            key="B_plant",
            display_en_name="Olive",
            display_heb_name="Zayit",
            all_en_names=["Olive"],
            all_heb_names=["Zayit"],
        )

        inserted_id = mixin.insert_entity(entity)

        self.assertEqual(inserted_id, "id42")
        doc = mixin.get_collection(CollectionObjs.ENTITIES).last_insert_one_doc
        self.assertEqual(doc[DBFields.ENTITY_TYPE], entity.entityType.value)

    def test_entity_doc_to_entity_returns_specific_subclass(self):
        mixin = DummyEntityMongo()
        doc = {
            DBFields.KEY: "B_plant",
            DBFields.DISPLAY_EN_NAME: "Olive",
            DBFields.DISPLAY_HEB_NAME: "Zayit",
            DBFields.ALL_EN_NAMES: ["Olive"],
            DBFields.ALL_HEB_NAMES: ["Zayit"],
            DBFields.ENTITY_TYPE: "B",
        }

        entity = mixin._doc_to_entity(doc)

        self.assertEqual(entity.__class__.__name__, "EPlant")
        self.assertEqual(entity.key, "B_plant")

    def test_relationship_get_rels_for_entity_uses_or_query(self):
        mixin = DummyRelationshipMongo()
        coll = mixin.get_collection(CollectionObjs.RELATIONS)
        coll.find_result = [{"key": "r", "term1": "A", "term2": "B", "rel_type": RelType.allyOf.value}]

        rels = mixin.get_rels_for_entity("A")

        self.assertEqual(len(rels), 1)
        self.assertIn(DBOperators.OR, coll.last_find_query)

    def test_relationship_doc_to_rel_casts_enum(self):
        mixin = DummyRelationshipMongo()
        rel = mixin._doc_to_rel(
            {"key": "r1", "term1": "a", "term2": "b", "rel_type": RelType.spokeWith.value}
        )

        self.assertIsInstance(rel, Rel)
        self.assertEqual(rel.rel_type, RelType.spokeWith)

    def test_faiss_save_and_load_roundtrip(self):
        mixin = DummyFaissMongo()
        coll = mixin.get_collection(CollectionObjs.FS)

        mixin.save_faiss_index(b"index-bytes", b"meta-bytes")
        query, update, upsert = coll.last_update_one
        self.assertEqual(query, {})
        self.assertTrue(upsert)
        self.assertIn(DBFields.FAISS_INDEX, update[DBOperators.SET])

        coll.find_one_result = {
            DBFields.FAISS_INDEX: update[DBOperators.SET][DBFields.FAISS_INDEX],
            DBFields.METADATA: update[DBOperators.SET][DBFields.METADATA],
        }

        loaded = mixin.load_faiss_index()
        self.assertEqual(loaded, (b"index-bytes", b"meta-bytes"))

    def test_source_content_requires_client_for_find(self):
        mixin = DummySourceContentMongo(has_client=False)
        with self.assertRaises(Exception):
            mixin.find_one(CollectionObjs.BT, "BT_Book_1_1")

    def test_source_content_get_all_filters_missing_fields(self):
        mixin = DummySourceContentMongo(has_client=True)
        coll = mixin.get_collection(CollectionObjs.BT)
        coll.find_result = [
            {"key": "BT_A_1_1", "content": ["en", "he", ""]},
            {"key": "BT_A_1_2"},
        ]

        results = mixin.get_all_src_contents_of_collection(CollectionObjs.BT)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].key, "BT_A_1_1")

    def test_source_metadata_to_doc_serializes_enums_and_sets(self):
        mixin = DummySourceMetadataMongo()
        src_metadata = SourceMetadata(
            source_type=SourceType.TN,
            summary_en="summary",
            summary_heb="summary_he",
            passage_types=[PassageType.Story],
            entity_keys={"E1", "E2"},
            rel_keys={"R1"},
        )
        src_metadata.key = "TN_Genesis_1_1"

        doc = mixin._src_metadata_to_doc(src_metadata)

        self.assertEqual(doc[DBFields.KEY], "TN_Genesis_1_1")
        self.assertEqual(doc[DBFields.SOURCE_TYPE], SourceType.TN.value)
        self.assertEqual(doc[DBFields.PASSAGE_TYPES], [PassageType.Story.value])
        self.assertCountEqual(doc[DBFields.ENTITY_KEYS], ["E1", "E2"])


if __name__ == "__main__":
    unittest.main()



