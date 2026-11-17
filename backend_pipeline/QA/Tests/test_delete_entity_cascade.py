import contextlib
import io
import unittest

from backend.db.Collections import CollectionObjs
from backend_pipeline.data_pipeline.one_time_scripts import delete_entity_cascade as cascade
from backend_pipeline.QA.Tests.test_remove_entity_family_relationships import CleanupDB


class DeleteEntityCascadeTests(unittest.TestCase):
    def setUp(self):
        self.db = CleanupDB()
        self.entities = self.db.get_collection(CollectionObjs.ENTITIES)
        self.relations = self.db.get_collection(CollectionObjs.RELATIONS)
        self.metadata = self.db.get_collection(CollectionObjs.SRC_METADATA)
        self.entities.insert_many([
            {"_id": "e1", "key": "target", "display_en_name": "Target", "entityType": "Person"},
            {"_id": "e2", "key": "other", "display_en_name": "Other", "entityType": "Person"},
        ])
        self.relations.insert_many([
            {"_id": "r1", "key": "r1", "term1": "target", "term2": "other", "rel_type": "visited"},
            {"_id": "r2", "key": "r2", "term1": "other", "term2": "target", "rel_type": "spouseOf"},
            {"_id": "r3", "key": "r3", "term1": "other", "term2": "third", "rel_type": "spokeWith"},
        ])
        self.metadata.insert_one({
            "_id": "s", "entity_keys": ["target", "other"], "rel_keys": ["r1", "r2", "r3"], "x": 1,
        })

    def run_cleanup(self, key="target", apply=False):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cascade.clean(self.db, key, apply)
        return output.getvalue()

    def test_alias_references_are_logged_but_left_alone(self):
        self.entities.insert_one({"_id": "e3", "key": "alias", "display_en_name": "Alias",
                                  "alias_keys": ["target"]})
        output = self.run_cleanup(apply=True)
        self.assertIn("NOT cleaned up", output)
        self.assertIn("(1 entities currently reference it)", output)
        self.assertIn("alias: Alias", output)
        self.assertEqual(self.entities.find_one({"key": "alias"})["alias_keys"], ["target"])

    def test_preview_changes_nothing(self):
        self.assertIn("Would delete the entity and 2 relationships", self.run_cleanup())
        self.assertEqual(len(self.entities.find()), 2)
        self.assertEqual(len(self.relations.find()), 3)
        self.assertEqual(self.db.transactions, 0)

    def test_apply_deletes_entity_relationships_and_references_only(self):
        self.assertIn("Deleted the entity and 2 relationships", self.run_cleanup(apply=True))
        self.assertEqual([e["key"] for e in self.entities.find()], ["other"])
        self.assertEqual([r["key"] for r in self.relations.find()], ["r3"])
        source = self.metadata.find_one({"_id": "s"})
        self.assertEqual(source["entity_keys"], ["other"])
        self.assertEqual(source["rel_keys"], ["r3"])
        self.assertEqual(source["x"], 1)
        with self.assertRaisesRegex(ValueError, "found 0"):
            self.run_cleanup(apply=True)

    def test_bad_inputs_fail_before_writes(self):
        for key in ("", " target", "missing"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_cleanup(key, apply=True)
        self.relations.insert_one({"_id": "bad", "term1": "target", "term2": "x", "rel_type": "visited"})
        with self.assertRaisesRegex(ValueError, "no usable key"):
            self.run_cleanup(apply=True)
        self.assertEqual(len(self.entities.find()), 2)
        self.assertEqual(len(self.relations.find()), 4)


if __name__ == "__main__":
    unittest.main()
