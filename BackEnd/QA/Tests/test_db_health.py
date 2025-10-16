import json
import unittest
import time

from numpy.ma.testutils import assert_equal

from BackEnd.DataPipeline.DB.Collection import Collection, CollectionName
from BackEnd.DataPipeline.DB.DBFactory import DBFactory
from BackEnd.General import Paths


class DatabaseHealthTests(unittest.TestCase):

    db_api = DBFactory.get_prod_db_mongo()

    @classmethod
    def setUpClass(cls):
        """Runs once before all tests to load queries into memory."""
        cls.queries = cls._load_all_queries()

    @staticmethod
    def _load_all_queries() -> dict:
        file_path = Paths.QA_MONGO_QUERIES
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_query(self, name: str) -> dict:
        """Retrieve a query by name."""
        if name not in self.queries:
            raise ValueError(f"Query '{name}' not found in queries.json")
        return self.queries[name]

    def setUp(self):
        """Runs before every test."""
        self._start_time = time.time()  # record start time
        print(f"\nRunning test: {self._testMethodName}")

    def tearDown(self):
        """Runs after every test."""
        elapsed = time.time() - self._start_time
        print(f"Test {self._testMethodName} finished in {elapsed:.3f} seconds")

    ###########################################  Misc Tests ##################################################33

    def test_foo(self):
        # coll = self.db_api.get_collection(CollectionName.BT)
        # result = coll.update_many({}, {"$unset": {"summary": ""}})
        # print(result.modified_count)
        pass

    ###########################################  Source Tests ##################################################33

    def test_valid_num_sources(self):
        assert_equal(self.count_all_documents(CollectionName.BT), 12488)
        assert_equal(self.count_all_documents(CollectionName.TN), 1773)

    def test_sources_not_empty(self):
        collections = [
            CollectionName.TN,
            CollectionName.BT
        ]

        # Queries to check
        query_names = [
            "check_en_content_empty",
            "check_heb_content_empty",
            "check_key_empty",
            # "check_summary_empty"
        ]

        failures = []

        for collection in collections:
            for query_name in query_names:
                query = self.get_query(query_name)
                # Find all documents that **match the "empty" condition**
                results = self.db_api.execute_query_with_collection(
                    {
                        "operation": "find",
                        "filter": query
                    },
                    collection=collection
                )

                for doc in results:
                    key = doc.get("key", "<no key>")
                    print(f"[FAIL] Collection {collection.name}, Query {query_name}, Key: {key}")
                    failures.append((collection.name, query_name, key))

        if failures:
            # Fail the test at the end, summarizing all failures
            fail_messages = "\n".join(
                f"Collection {c}, Query {q}, Key {k}" for c, q, k in failures
            )
            self.fail(f"Some sources failed validation:\n{fail_messages}")

    def test_sources_valid_key(self):
        collections = [CollectionName.BT, CollectionName.TN]
        all_valid = True

        for col in collections:
            invalid_keys = self.get_invalid_keys(col)
            if invalid_keys:
                all_valid = False
                print(f"\nCollection '{col.name}' has invalid keys:")
                for key in invalid_keys:
                    print(f"  - {key}")

        assert all_valid, "Some documents have invalid key format!"

    def test_basic_functions_with_db(self):

        test_collection = CollectionName.TN #any random collection

        # Insert example data into collection
        data = {
            "key": "example_key",
            "content": "This is the content of the Talmud passage."
        }
        doc_id = self.db_api.insert(test_collection, data)
        # print(f"Inserted document ID: {doc_id}")

        # Query data
        query_results = self.db_api.execute_raw_query({
            "collection": test_collection,
            "filter": {"key": "example_key"}
        })
        # print(f"Query results: {query_results}")

        # Update data
        updated_rows = self.db_api.update(
            test_collection,
            {"key": "example_key"},
            {"content": "Updated content of the Talmud passage."}
        )
        # print(f"Updated {updated_rows} rows.")

        # Delete data
        deleted_rows = self.db_api.delete_instance(
            test_collection,
            {"key": "example_key"}
        )
        # print(f"Deleted {deleted_rows} rows.")

    ############################################## Helper Functions ####################################################
    def count_all_documents(self, collection:Collection) -> int:
        query = self.get_query("count_all_documents")  # assumes queries are loaded in the class
        count = self.db_api.execute_query_with_collection(
            {
                "operation": "count_documents",
                "filter": query
            },
            collection=collection
        )
        return count

    def get_invalid_keys(self, collection: Collection) -> list[str]:
        """Return a list of keys that do not match the expected format."""
        results = self.db_api.execute_query_with_collection(
            {
                "operation": "find",
                "filter": self.get_query("check_key_format")
            },
            collection=collection
        )
        return [doc.get("key") for doc in results] if results else []

    ###################################################################

if __name__ == "__main__":
    unittest.main()