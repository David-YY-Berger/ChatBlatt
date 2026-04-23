import unittest
import inspect
from unittest.mock import MagicMock, patch

from backend.db.Collections import Collection
from backend.db.DBapiMongoDB import DBapiMongoDB


class FakeCollection:
    def __init__(self):
        self.last_call = None

    def find(self, filt):
        self.last_call = ("find", filt)
        return [{"x": 1}]

    def update_one(self, filt, update):
        self.last_call = ("update_one", filt, update)
        return MagicMock(raw_result={"ok": 1})

    def update_many(self, filt, update):
        self.last_call = ("update_many", filt, update)
        return MagicMock(raw_result={"ok": 1}, modified_count=2)

    def delete_one(self, filt):
        self.last_call = ("delete_one", filt)
        return MagicMock(raw_result={"ok": 1})

    def delete_many(self, filt):
        self.last_call = ("delete_many", filt)
        return MagicMock(raw_result={"ok": 1}, deleted_count=3)

    def insert_one(self, doc):
        self.last_call = ("insert_one", doc)
        return MagicMock(inserted_id="id1")

    def insert_many(self, docs):
        self.last_call = ("insert_many", docs)
        return MagicMock(inserted_ids=["id1", "id2"])

    def count_documents(self, filt):
        self.last_call = ("count_documents", filt)
        return 12

    def replace_one(self, filt, replacement):
        self.last_call = ("replace_one", filt, replacement)
        return MagicMock(raw_result={"ok": 1})

    def aggregate(self, pipeline):
        self.last_call = ("aggregate", pipeline)
        return [{"sum": 10}]

    def find_one(self, filt):
        self.last_call = ("find_one", filt)
        return {"x": 1}

    def distinct(self, field, filt):
        self.last_call = ("distinct", field, filt)
        return ["a", "b"]


class DBapiMongoCoreTests(unittest.TestCase):
    def _new_dbapi_instance(self):
        raw_cls = inspect.unwrap(DBapiMongoDB)
        return raw_cls()

    def test_get_collection_raises_for_unknown_db(self):
        dbapi = self._new_dbapi_instance()
        with self.assertRaises(ValueError):
            dbapi.get_collection(Collection("missing", "unknown_db"))

    def test_execute_raw_query_dispatches_find(self):
        dbapi = self._new_dbapi_instance()
        collection = Collection("c1", "db1")
        fake = FakeCollection()
        dbapi.dbs = {"db1": {"c1": fake}}

        result = dbapi.execute_raw_query({"collection": collection, "operation": "find", "filter": {"x": 1}})

        self.assertEqual(result, [{"x": 1}])
        self.assertEqual(fake.last_call, ("find", {"x": 1}))

    def test_execute_raw_query_unsupported_operation(self):
        dbapi = self._new_dbapi_instance()
        collection = Collection("c1", "db1")
        dbapi.dbs = {"db1": {"c1": FakeCollection()}}

        with self.assertRaises(ValueError):
            dbapi.execute_raw_query({"collection": collection, "operation": "nope"})

    def test_execute_query_with_collection_injects_collection(self):
        dbapi = self._new_dbapi_instance()
        collection = Collection("c1", "db1")
        dbapi.dbs = {"db1": {"c1": FakeCollection()}}

        result = dbapi.execute_query_with_collection({"operation": "count_documents"}, collection)

        self.assertEqual(result, 12)

    def test_insert_update_delete_collection_methods(self):
        dbapi = self._new_dbapi_instance()
        dbapi.client = object()
        collection = Collection("c1", "db1")
        fake = FakeCollection()
        dbapi.dbs = {"db1": {"c1": fake}}

        inserted = dbapi.insert(collection, {"key": "k1"})
        modified = dbapi.update(collection, {"key": "k1"}, {"field": 1})
        deleted = dbapi.delete_instance(collection, {"key": "k1"})
        deleted_all = dbapi.delete_collection(collection)

        self.assertEqual(inserted, "id1")
        self.assertEqual(modified, 2)
        self.assertEqual(deleted, 3)
        self.assertEqual(deleted_all, 3)

    @patch("backend.db.DBapiMongoDB.MongoClient")
    def test_connect_and_disconnect_are_local_and_manage_state(self, mongo_client_mock):
        dbapi = self._new_dbapi_instance()

        client_instance = MagicMock()
        client_instance.admin.command.return_value = {"ok": 1}
        client_instance.get_database.side_effect = lambda name: {"_db_name": name}
        mongo_client_mock.return_value = client_instance

        dbapi.connect("mongodb://unit-test")

        self.assertIs(dbapi.client, client_instance)
        self.assertGreaterEqual(len(dbapi.dbs), 1)
        self.assertTrue(client_instance.admin.command.called)

        dbapi.disconnect()

        self.assertIsNone(dbapi.client)
        self.assertEqual(dbapi.dbs, {})


if __name__ == "__main__":
    unittest.main()


