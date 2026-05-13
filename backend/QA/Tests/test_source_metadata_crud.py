# # bs"d
# """CRUD tests for SourceMetadata via SourceMetadataMongoMixin."""
# import logging, unittest
# from backend.QA.Tests.conftest import FakeDBapi, TEST_SOURCE_KEY
# from backend.db.Collections import CollectionObjs
# from backend.models_db.Enums import SourceType, PassageType
# from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
#
# logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
# log = logging.getLogger(__name__)
#
#
# def _meta(key=TEST_SOURCE_KEY):
#     sm = SourceMetadata(TEST_SOURCE_KEY)
#     sm.summary_en = "Test summary"
#     sm.summary_heb = "סיכום בדיקה"
#     sm.passage_types = [PassageType.Law, PassageType.Story]
#     sm.entity_keys = {"__test_P_Moses", "__test_L_Jerusalem"}
#     sm.rel_keys = {"__test_rel_1"}
#     return sm
#
#
# class TestSourceMetadataCRUD(unittest.TestCase):
#     def setUp(self):
#         self.db = FakeDBapi.create()
#         self.meta = _meta()
#
#     # -- CREATE --
#     def test_insert(self):
#         mid = self.db.insert_source_metadata(self.meta)
#         self.assertTrue(mid, "INSERT source_metadata returned falsy id")
#
#     # -- READ --
#     def test_read_by_key(self):
#         self.db.insert_source_metadata(self.meta)
#         r = self.db.get_source_metadata_by_key(self.meta.key)
#         self.assertIsNotNone(r, f"READ None for key={self.meta.key}")
#         self.assertEqual(r.key, self.meta.key)
#         self.assertEqual(r.source_type, SourceType.TN, f"source_type mismatch: {r.source_type}")
#         self.assertEqual(r.summary_en, "Test summary", f"summary_en mismatch")
#         self.assertEqual(set(r.entity_keys), self.meta.entity_keys, "entity_keys mismatch")
#         self.assertEqual(set(r.rel_keys), self.meta.rel_keys, "rel_keys mismatch")
#         self.assertEqual(len(r.passage_types), 2, f"passage_types count mismatch")
#
#     # -- READ missing --
#     def test_read_missing_returns_none(self):
#         self.assertIsNone(self.db.get_source_metadata_by_key("__test_NONEXISTENT"))
#
#     # -- EXISTS --
#     def test_exists(self):
#         self.assertFalse(self.db.is_src_metadata_exists(self.meta.key))
#         self.db.insert_source_metadata(self.meta)
#         self.assertTrue(self.db.is_src_metadata_exists(self.meta.key))
#
#     # -- UPDATE --
#     def test_update(self):
#         self.db.insert_source_metadata(self.meta)
#         updated = _meta()
#         updated.summary_en = "Updated summary"
#         updated.passage_types = [PassageType.PROPHECY]
#         modified = self.db.update_source_metadata(updated)
#         self.assertEqual(modified, 1, "UPDATE modified!=1")
#         r = self.db.get_source_metadata_by_key(self.meta.key)
#         self.assertEqual(r.summary_en, "Updated summary", "UPDATE summary not persisted")
#         self.assertEqual(len(r.passage_types), 1, "UPDATE passage_types not persisted")
#
#     # -- DELETE --
#     def test_delete(self):
#         self.db.insert_source_metadata(self.meta)
#         d = self.db.get_collection(CollectionObjs.SRC_METADATA).delete_many({"key": self.meta.key}).deleted_count
#         self.assertEqual(d, 1, "DELETE count!=1")
#         self.assertIsNone(self.db.get_source_metadata_by_key(self.meta.key), "DELETE still readable")
#
#     # -- READ all --
#     def test_get_all(self):
#         self.db.insert_source_metadata(self.meta)
#         m2 = _meta(key=TEST_SOURCE_KEY)
#         m2.source_type = SourceType.TN
#         m2.summary_en = "Another summary"
#         self.db.insert_source_metadata(m2)
#         results = self.db.get_all_source_metadata()
#         self.assertEqual(len(results), 2, f"get_all returned {len(results)}, expected 2")
#
#     # -- UPSERT (interface default) --
#     def test_upsert_insert_path(self):
#         result = self.db.upsert_source_metadata(self.meta)
#         self.assertTrue(result, "UPSERT insert path returned falsy")
#
#     def test_upsert_update_path(self):
#         self.db.insert_source_metadata(self.meta)
#         self.meta.summary_en = "Via upsert"
#         result = self.db.upsert_source_metadata(self.meta)
#         self.assertEqual(result, self.meta.key)
#         r = self.db.get_source_metadata_by_key(self.meta.key)
#         self.assertEqual(r.summary_en, "Via upsert", "UPSERT update not persisted")
#
#
# if __name__ == "__main__":
#     unittest.main()
#
#
