import unittest
from unittest.mock import MagicMock

from backend.db.Collections import CollectionObjs
from backend.models_db.EntityObjects.ENumber import ENumber
from backend.models_db.Enums import EntityType, RelType
from backend_pipeline.data_pipeline.one_time_scripts.clean_folio_page_numbers import clean
from backend_pipeline.data_pipeline.populator_scripts import DBPopulateEntityRelGraph as population
from backend_pipeline.QA.Tests.conftest import FakeCollection


class CleanupCollection(FakeCollection):
    def update_many(self, filt, update):
        if "$pull" not in update:
            return super().update_many(filt, update)
        count = 0
        for doc in self._docs:
            if self._matches(doc, filt):
                for field, value in update["$pull"].items():
                    values = value["$in"] if isinstance(value, dict) else [value]
                    doc[field] = [item for item in doc.get(field, []) if item not in values]
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
            collection: CleanupCollection()
            for collection in (CollectionObjs.ENTITIES, CollectionObjs.RELATIONS, CollectionObjs.SRC_METADATA)
        }

    def get_collection(self, collection):
        return self.collections[collection]

    def run_in_transaction(self, callback):
        return callback()


class CitationNumberTests(unittest.TestCase):
    def test_number_filter_preserves_existing_rules(self):
        for unit in ("verse", "folio", "page", " Folio ", " PAGE "):
            with self.subTest(unit=unit):
                self.assertTrue(population._is_ignored_number(ENumber(display_en_name="5", en_unit=unit)))
        for unit in ("pages", "folio of parchment", "year", None):
            with self.subTest(unit=unit):
                self.assertFalse(population._is_ignored_number(ENumber(display_en_name="5", en_unit=unit)))
        for value in ("0", "1"):
            self.assertTrue(population._is_ignored_number(ENumber(display_en_name=value, en_unit="year")))

    def test_population_skips_number_and_its_relationship(self):
        populator = population.DBPopulateEntityRelGraph()
        populator.db_api = MagicMock()
        ignored = set()
        source_map = {}
        number = {"en_name": "5", "en_unit": " Page "}
        result = populator._try_insert_entity("source", {}, number, EntityType.ENumber, source_map, ignored)
        self.assertIsNone(result)
        self.assertEqual(len(ignored), 1)
        rel = populator._try_insert_rel(
            {"term1": "Moses", "term2": "5"}, RelType.spokeWith, "spokeWith",
            "source", {"Number": [number]}, {("moses", EntityType.EPerson): "person"}, ignored,
        )
        self.assertIsNone(rel)
        populator.db_api.try_insert_number.assert_not_called()
        populator.db_api.try_insert_rel.assert_not_called()

    def test_cleanup_preview_apply_and_repeat(self):
        db = CleanupDB()
        entities = db.get_collection(CollectionObjs.ENTITIES)
        relations = db.get_collection(CollectionObjs.RELATIONS)
        metadata = db.get_collection(CollectionObjs.SRC_METADATA)
        entities.insert_many([
            {"_id": "n1", "key": "n1", "entityType": "Number", "en_unit": " Folio ", "display_en_name": "5"},
            {"_id": "n2", "key": "n2", "entityType": "Number", "en_unit": "PAGE", "display_en_name": "6"},
            {"_id": "n3", "key": "n3", "entityType": "Number", "en_unit": "verse", "display_en_name": "7"},
            {"_id": "n4", "key": "n4", "entityType": "Number", "en_unit": "pages", "display_en_name": "8"},
            {"_id": "p", "key": "p", "entityType": "Person", "en_unit": "page"},
        ])
        relations.insert_many([
            {"_id": "r1", "key": "r1", "term1": "n1", "term2": "p"},
            {"_id": "r2", "key": "r2", "term1": "n2", "term2": "n1"},
            {"_id": "r3", "key": "r3", "term1": "p", "term2": "n3"},
        ])
        metadata.insert_one({
            "_id": "s1", "entity_keys": ["n1", "n2", "n3", "p"],
            "rel_keys": ["r1", "r2", "r3"], "other": "keep",
        })
        clean(db, False)
        self.assertEqual(len(entities.find()), 5)
        self.assertEqual(len(relations.find()), 3)
        self.assertEqual(metadata.find_one({"_id": "s1"})["entity_keys"], ["n1", "n2", "n3", "p"])

        clean(db, True)
        clean(db, True)
        self.assertEqual({doc["key"] for doc in entities.find()}, {"n3", "n4", "p"})
        self.assertEqual([doc["key"] for doc in relations.find()], ["r3"])
        source = metadata.find_one({"_id": "s1"})
        self.assertEqual(source["entity_keys"], ["n3", "p"])
        self.assertEqual(source["rel_keys"], ["r3"])
        self.assertEqual(source["other"], "keep")

    def test_missing_relationship_key_stops_before_writing(self):
        db = CleanupDB()
        entities = db.get_collection(CollectionObjs.ENTITIES)
        relations = db.get_collection(CollectionObjs.RELATIONS)
        entities.insert_one({"_id": "n", "key": "n", "entityType": "Number", "en_unit": "page"})
        relations.insert_one({"_id": "r", "term1": "n", "term2": "other"})
        with self.assertRaisesRegex(ValueError, "no usable key"):
            clean(db, True)
        self.assertEqual(len(entities.find()), 1)
        self.assertEqual(len(relations.find()), 1)


if __name__ == "__main__":
    unittest.main()
