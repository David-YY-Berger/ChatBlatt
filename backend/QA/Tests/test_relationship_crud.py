# # bs"d
# """CRUD tests for Relationship (Rel) via RelationshipMongoMixin."""
# import logging, unittest
# from backend.QA.Tests.conftest import FakeDBapi
# from backend.models_db.Enums import RelType
# from backend.models_db.Rel import Rel
#
# logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
# log = logging.getLogger(__name__)
#
# def _rel(key="__test_rel_1", t1="__test_P_Moses", t2="__test_P_Amram", rt=RelType.childOfFather):
#     return Rel(key=key, term1=t1, term2=t2, rel_type=rt)
#
# class TestRelCRUD(unittest.TestCase):
#     def setUp(self):
#         self.db = FakeDBapi.create()
#         self.rel = _rel()
#         self.rel_upd = Rel(key=self.rel.key, term1="__test_P_Moses", term2="__test_P_Amram_v2", rel_type=RelType.childOfFather)
#
#     def test_insert(self):
#         rid = self.db.insert_rel(self.rel)
#         self.assertTrue(rid, "INSERT rel returned falsy id")
#
#     def test_read_by_key(self):
#         self.db.insert_rel(self.rel)
#         r = self.db.get_rel_by_key(self.rel.key)
#         self.assertIsNotNone(r, f"READ rel None for key={self.rel.key}")
#         self.assertEqual(r.key, self.rel.key, f"key mismatch: {r.key}")
#         self.assertEqual(r.rel_type, self.rel.rel_type, f"rel_type mismatch")
#
#     def test_read_by_keys(self):
#         r2 = _rel(key="__test_rel_2", rt=RelType.childOfMother, t2="__test_P_Yocheved")
#         self.db.insert_rel(self.rel); self.db.insert_rel(r2)
#         self.assertEqual(len(self.db.get_rels_by_keys([self.rel.key, r2.key])), 2)
#
#     def test_rels_for_entity(self):
#         self.db.insert_rel(self.rel)
#         self.assertGreaterEqual(len(self.db.get_rels_for_entity("__test_P_Moses")), 1, "0 rels for term1")
#         self.assertGreaterEqual(len(self.db.get_rels_for_entity("__test_P_Amram")), 1, "0 rels for term2")
#
#     def test_all_rels(self):
#         self.db.insert_rel(self.rel)
#         self.assertGreaterEqual(len(self.db.get_all_rels()), 1)
#
#     def test_exists(self):
#         self.assertFalse(self.db.is_rel_exists(self.rel.key))
#         self.db.insert_rel(self.rel)
#         self.assertTrue(self.db.is_rel_exists(self.rel.key))
#
#     def test_update(self):
#         self.db.insert_rel(self.rel)
#         self.assertEqual(self.db.update_rel(self.rel_upd), 1, "UPDATE modified!=1")
#         self.assertEqual(self.db.get_rel_by_key(self.rel.key).term2, self.rel_upd.term2, "UPDATE term2 not persisted")
#
#     def test_delete(self):
#         from backend.db.Collections import CollectionObjs
#         self.db.insert_rel(self.rel)
#         d = self.db.get_collection(CollectionObjs.RELATIONS).delete_many({"key": self.rel.key}).deleted_count
#         self.assertEqual(d, 1, "DELETE count!=1")
#         self.assertIsNone(self.db.get_rel_by_key(self.rel.key), "DELETE rel still readable")
#
#     def test_bulk_insert(self):
#         r2 = _rel(key="__test_rel_3", rt=RelType.spouseOf, t2="__test_P_Tzipporah")
#         self.assertEqual(self.db.insert_rels_bulk([self.rel, r2]), 2)
#
#     def test_bulk_insert_empty(self):
#         self.assertEqual(self.db.insert_rels_bulk([]), 0)
#
#     def test_upsert_bulk_insert(self):
#         u, m = self.db.upsert_rels_bulk([self.rel])
#         self.assertEqual(u, 1, "UPSERT upserted!=1")
#
#     def test_upsert_bulk_update(self):
#         self.db.insert_rel(self.rel)
#         u, m = self.db.upsert_rels_bulk([self.rel_upd])
#         self.assertEqual(m, 1, "UPSERT modified!=1")
#
# if __name__ == "__main__":
#     unittest.main()
#
