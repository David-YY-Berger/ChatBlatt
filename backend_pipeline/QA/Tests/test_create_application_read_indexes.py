import unittest
from unittest.mock import MagicMock

from backend_pipeline.data_pipeline.one_time_scripts.create_application_read_indexes import (
    INDEX_KEYS,
    INDEX_NAME,
    create_missing_indexes,
)


class CreateApplicationReadIndexesTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.list_collection_names.return_value = ["TN", "BT"]
        self.collections = {name: MagicMock() for name in ("TN", "BT")}
        self.db.__getitem__.side_effect = self.collections.__getitem__
        for collection in self.collections.values():
            collection.list_indexes.return_value = [{"name": "_id_", "key": {"_id": 1}}]

    def test_dry_run_and_apply_are_limited_to_source_key_indexes(self):
        create_missing_indexes(self.db, False)
        for collection in self.collections.values():
            collection.create_index.assert_not_called()

        create_missing_indexes(self.db, True)
        for collection in self.collections.values():
            collection.create_index.assert_called_once_with(INDEX_KEYS, name=INDEX_NAME)

    def test_existing_usable_index_is_not_duplicated(self):
        self.collections["TN"].list_indexes.return_value = [
            {"name": "other", "key": {"key": 1, "other": 1}}
        ]
        create_missing_indexes(self.db, True)
        self.collections["TN"].create_index.assert_not_called()
        self.collections["BT"].create_index.assert_called_once()

    def test_conflicting_index_is_not_silently_accepted(self):
        self.collections["TN"].list_indexes.return_value = [
            {"name": "partial", "key": {"key": 1}, "partialFilterExpression": {"key": {"$exists": True}}}
        ]
        with self.assertRaisesRegex(RuntimeError, "conflicting key index"):
            create_missing_indexes(self.db, True)
        self.collections["TN"].create_index.assert_not_called()

    def test_missing_collection_does_not_create_any_indexes(self):
        self.db.list_collection_names.return_value = ["TN"]
        with self.assertRaisesRegex(RuntimeError, "Sources.BT does not exist"):
            create_missing_indexes(self.db, True)
        self.collections["TN"].create_index.assert_not_called()


if __name__ == "__main__":
    unittest.main()
