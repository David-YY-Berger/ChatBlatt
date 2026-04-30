# bs"d
"""CRUD tests for FAISS index save/load via FaissMongoMixin."""
import logging, unittest
from backend.QA.Tests.conftest import FakeDBapi

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


class TestFaissCRUD(unittest.TestCase):
    def setUp(self):
        self.db = FakeDBapi.create()

    # -- SAVE + LOAD (Create + Read) --
    def test_save_and_load(self):
        idx = b"\x00\x01\x02FAISS_INDEX_BYTES"
        meta = b"\x00\x01\x02METADATA_BYTES"
        self.db.save_faiss_index(idx, meta)
        result = self.db.load_faiss_index()
        self.assertIsNotNone(result, "load_faiss_index returned None after save")
        loaded_idx, loaded_meta = result
        self.assertEqual(loaded_idx, idx, f"FAISS index bytes mismatch")
        self.assertEqual(loaded_meta, meta, f"FAISS metadata bytes mismatch")
        log.info("SAVE+LOAD OK  FAISS")

    # -- LOAD when nothing saved --
    def test_load_empty(self):
        result = self.db.load_faiss_index()
        self.assertIsNone(result, "load_faiss_index should return None when nothing saved")

    # -- UPDATE (upsert semantics – save again overwrites) --
    def test_save_overwrites(self):
        self.db.save_faiss_index(b"old_idx", b"old_meta")
        self.db.save_faiss_index(b"new_idx", b"new_meta")
        loaded_idx, loaded_meta = self.db.load_faiss_index()
        self.assertEqual(loaded_idx, b"new_idx", "Second save did not overwrite index")
        self.assertEqual(loaded_meta, b"new_meta", "Second save did not overwrite metadata")

    # -- Large payload --
    def test_large_payload(self):
        big_idx = b"\xff" * 100_000
        big_meta = b"\xfe" * 50_000
        self.db.save_faiss_index(big_idx, big_meta)
        loaded_idx, loaded_meta = self.db.load_faiss_index()
        self.assertEqual(len(loaded_idx), 100_000, "Large index size mismatch")
        self.assertEqual(len(loaded_meta), 50_000, "Large metadata size mismatch")

    # -- DELETE (clear collection) --
    def test_delete_faiss(self):
        from backend.db.Collections import CollectionObjs
        self.db.save_faiss_index(b"idx", b"meta")
        self.db.get_collection(CollectionObjs.FS).delete_many({})
        self.assertIsNone(self.db.load_faiss_index(), "FAISS still readable after delete")


if __name__ == "__main__":
    unittest.main()

