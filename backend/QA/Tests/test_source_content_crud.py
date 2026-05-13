# # bs"d
# """CRUD tests for SourceContent via SourceContentMongoMixin."""
# import logging, unittest
# from backend.QA.Tests.conftest import FakeDBapi, TEST_SOURCE_KEY
# from backend.db.Collections import CollectionObjs
# from backend.models_db.SourceClasses.SourceContent import SourceContent
#
# logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
# log = logging.getLogger(__name__)
#
# _KEY = TEST_SOURCE_KEY
# _CONTENT = ["<b>English</b> text", "<b>Hebrew</b> טקסט", ""]
#
#
# class TestSourceContentCRUD(unittest.TestCase):
#     def setUp(self):
#         self.db = FakeDBapi.create()
#         self.col = CollectionObjs.BT
#
#     # -- CREATE via low-level insert --
#     def test_insert_and_find_one(self):
#         self.db.get_collection(self.col).insert_one({"key": _KEY, "content": _CONTENT})
#         doc = self.db.find_one(self.col, _KEY)
#         self.assertIsNotNone(doc, f"find_one returned None after insert for key={_KEY}")
#         self.assertEqual(doc["key"], _KEY, f"key mismatch: {doc['key']}")
#         log.info("INSERT+READ OK  SourceContent key=%s", _KEY)
#
#     # -- READ as SourceContent object --
#     def test_find_one_source_content_by_col(self):
#         self.db.get_collection(self.col).insert_one({"key": _KEY, "content": _CONTENT})
#         sc = self.db._find_one_source_content_by_col(self.col, _KEY)
#         self.assertIsInstance(sc, SourceContent, f"Expected SourceContent, got {type(sc)}")
#         self.assertEqual(sc.key, _KEY)
#         self.assertEqual(len(sc.content), 3, f"content length mismatch: {len(sc.content)}")
#
#     # -- READ missing key raises --
#     def test_find_one_source_content_missing_raises(self):
#         with self.assertRaises(Exception, msg="Expected exception for missing key"):
#             self.db._find_one_source_content_by_col(self.col, "__test_NONEXISTENT")
#
#     # -- EXISTS --
#     def test_exists(self):
#         self.assertFalse(self.db.find_one(self.col, _KEY), "exists True before insert")
#         self.db.get_collection(self.col).insert_one({"key": _KEY, "content": _CONTENT})
#         self.assertTrue(self.db.find_one(self.col, _KEY), "exists False after insert")
#
#     # -- READ all --
#     def test_get_all_src_contents(self):
#         self.db.get_collection(self.col).insert_one({"key": _KEY, "content": _CONTENT})
#         results = self.db.get_all_src_contents_of_collection(self.col)
#         self.assertGreaterEqual(len(results), 1, "get_all returned 0")
#         self.assertIsInstance(results[0], SourceContent)
#
#     # -- UPDATE --
#     def test_update_content(self):
#         self.db.get_collection(self.col).insert_one({"key": _KEY, "content": _CONTENT})
#         new_content = ["Updated EN", "Updated HEB", "clean"]
#         self.db.get_collection(self.col).update_one({"key": _KEY}, {"$set": {"content": new_content}})
#         doc = self.db.find_one(self.col, _KEY)
#         self.assertEqual(doc["content"], new_content, "UPDATE content not persisted")
#
#     # -- DELETE --
#     def test_delete(self):
#         self.db.get_collection(self.col).insert_one({"key": _KEY, "content": _CONTENT})
#         d = self.db.get_collection(self.col).delete_many({"key": _KEY}).deleted_count
#         self.assertEqual(d, 1, "DELETE count!=1")
#         self.assertIsNone(self.db.find_one(self.col, _KEY), "DELETE doc still readable")
#
#     # -- SourceContent model validation --
#     def test_source_content_validation(self):
#         sc = SourceContent(key=_KEY, content=_CONTENT)
#         errors = sc.is_valid_else_get_error_list()
#         self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
#
#     def test_source_content_empty_content_invalid(self):
#         sc = SourceContent(key=_KEY, content=["", "", ""])
#         errors = sc.is_valid_else_get_error_list()
#         self.assertGreater(len(errors), 0, "Empty content should produce validation errors")
#
#     # -- Multiple collections --
#     def test_different_collections_isolated(self):
#         self.db.get_collection(CollectionObjs.BT).insert_one({"key": _KEY, "content": _CONTENT})
#         self.assertIsNone(self.db.find_one(CollectionObjs.TN, _KEY),
#                           "Doc inserted into BT should not appear in TN")
#
#
# if __name__ == "__main__":
#     unittest.main()
#
#
#
