import unittest
from unittest.mock import MagicMock, patch

from backend_pipeline.data_pipeline.one_time_scripts import create_application_read_indexes as script
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

    def test_apply_switch_and_flag_select_write_credentials(self):
        for configured_apply, arguments, expected in (
            (False, [], False),
            (True, [], True),
            (False, ["--apply"], True),
        ):
            with self.subTest(configured_apply=configured_apply, arguments=arguments), \
                 patch("sys.argv", ["script", *arguments]), \
                 patch.object(script.DBFactory, "get_prod_mongo_uri", return_value="read") as read_uri, \
                 patch.object(script.DBFactory, "get_population_mongo_uri", return_value="write") as write_uri, \
                 patch.object(script, "MongoClient") as client, \
                 patch.object(script, "create_missing_indexes") as create:
                script.main(configured_apply)
                client.assert_called_once_with("write" if expected else "read", serverSelectionTimeoutMS=10000)
                create.assert_called_once_with(client.return_value.__enter__.return_value["Sources"], expected)
                self.assertEqual(read_uri.call_count, int(not expected))
                self.assertEqual(write_uri.call_count, int(expected))


if __name__ == "__main__":
    unittest.main()
