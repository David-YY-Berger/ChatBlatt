import contextlib
import io
import unittest
from unittest.mock import MagicMock

from backend.db.Collections import CollectionObjs
from backend.db.mongo_parts.genealogy_mixin import GenealogyMongoMixin
from backend_pipeline.data_pipeline.one_time_scripts import remove_entity_family_relationships as cleanup
from backend_pipeline.QA.Tests.conftest import FakeCollection


class MetadataCollection(FakeCollection):
    def _matches(self, doc, filt):
        # Real MongoDB matches a scalar against array fields by membership.
        scalar = {k: v for k, v in filt.items()
                  if not isinstance(v, dict) and k not in ("$or", "$and") and isinstance(doc.get(k), list)}
        if any(v not in doc[k] for k, v in scalar.items()):
            return False
        rest = {k: v for k, v in filt.items() if k not in scalar}
        return super()._matches(doc, rest)

    def update_many(self, filt, update):
        count = 0
        for doc in self._docs:
            if self._matches(doc, filt):
                for field, value in update["$pull"].items():
                    values = value["$in"] if isinstance(value, dict) else [value]
                    doc[field] = [item for item in doc[field] if item not in values]
                count += 1
        return MagicMock(modified_count=count)

    def delete_one(self, filt):
        for index, doc in enumerate(self._docs):
            if self._matches(doc, filt):
                self._docs.pop(index)
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)


class CleanupDB:
    def __init__(self):
        self.collections = {
            CollectionObjs.ENTITIES: MetadataCollection(),
            CollectionObjs.RELATIONS: MetadataCollection(),
            CollectionObjs.SRC_METADATA: MetadataCollection(),
        }
        self.transactions = 0

    def get_collection(self, collection):
        return self.collections[collection]

    def run_in_transaction(self, callback):
        self.transactions += 1
        return callback()


class RemoveEntityFamilyRelationshipsTests(unittest.TestCase):
    def setUp(self):
        self.db = CleanupDB()
        self.entities = self.db.get_collection(CollectionObjs.ENTITIES)
        self.relations = self.db.get_collection(CollectionObjs.RELATIONS)
        self.metadata = self.db.get_collection(CollectionObjs.SRC_METADATA)
        self.entities.insert_one({"key": "target", "display_en_name": "Target"})
        self.relations.insert_many([
            {"_id": "r1", "key": "r1", "term1": "target", "term2": "other", "rel_type": "childOfFather"},
            {"_id": "r2", "key": "r2", "term1": "other", "term2": "target", "rel_type": "childOfMother"},
            {"_id": "r3", "key": "r3", "term1": "target", "term2": "other", "rel_type": "spouseOf"},
            {"_id": "r4", "key": "r4", "term1": "other", "term2": "target", "rel_type": "descendantOf"},
            {"_id": "r5", "key": "r5", "term1": "target", "term2": "other", "rel_type": "spokeWith"},
            {"_id": "r6", "key": "r6", "term1": "other", "term2": "third", "rel_type": "spouseOf"},
        ])
        self.metadata.insert_one({
            "_id": "source", "rel_keys": ["r1", "r2", "r3", "r4", "r5", "r6"],
            "entity_keys": ["target", "other"], "other": "keep",
        })

    def run_cleanup(self, key="target", apply=False):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cleanup.clean(self.db, key, apply)
        return output.getvalue()

    def test_preview_apply_and_repeat(self):
        preview = self.run_cleanup()
        self.assertIn("Would remove 4 relationships", preview)
        self.assertIn("r4: other --descendantOf--> target", preview)
        self.assertEqual(len(self.relations.find()), 6)
        self.assertEqual(len(self.metadata.find_one({"_id": "source"})["rel_keys"]), 6)
        self.assertEqual(self.db.transactions, 0)

        self.assertIn("Removed 4 relationships", self.run_cleanup(apply=True))
        self.assertEqual(self.db.transactions, 1)
        self.assertEqual({doc["key"] for doc in self.relations.find()}, {"r5", "r6"})
        source = self.metadata.find_one({"_id": "source"})
        self.assertEqual(source["rel_keys"], ["r5", "r6"])
        self.assertEqual(source["entity_keys"], ["target", "other"])
        self.assertEqual(source["other"], "keep")
        self.assertIsNotNone(self.entities.find_one({"key": "target"}))
        self.assertIn("Removed 0 relationships", self.run_cleanup(apply=True))

    def test_missing_entity_and_bad_relationship_keys_fail_before_writes(self):
        for key in ("missing", "", " target"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_cleanup(key, apply=True)
        self.relations.insert_one({"_id": "bad", "term1": "target", "term2": "other",
                                   "rel_type": "spouseOf"})
        with self.assertRaisesRegex(ValueError, "no usable key"):
            self.run_cleanup(apply=True)
        self.assertEqual(len(self.relations.find()), 7)
        self.assertEqual(len(self.metadata.find_one({"_id": "source"})["rel_keys"]), 6)

    def test_duplicate_relationship_keys_fail_before_writes(self):
        self.relations.insert_one({"_id": "duplicate", "key": "r1", "term1": "other",
                                   "term2": "third", "rel_type": "spokeWith"})
        with self.assertRaisesRegex(ValueError, "not unique"):
            self.run_cleanup(apply=True)
        self.assertEqual(len(self.relations.find()), 7)

    def test_direct_family_tree_still_excludes_descendants(self):
        relations = self.relations

        class GenealogyDB(GenealogyMongoMixin):
            def get_collection(self, collection):
                return relations

            def _doc_to_rel(self, doc):
                return doc

        db = GenealogyDB()
        self.assertEqual(
            {rel["key"] for rel in db.get_family_rels_for_entity("target")},
            {"r1", "r2", "r3"},
        )
        self.assertEqual(
            {rel["key"] for rel in db.get_family_rels_for_entities(["target"])},
            {"r1", "r2", "r3"},
        )


if __name__ == "__main__":
    unittest.main()
