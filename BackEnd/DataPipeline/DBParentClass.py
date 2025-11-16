import unittest
import json
import time
from pathlib import Path

from BackEnd.DataPipeline.DB.DBFactory import DBFactory
from BackEnd.FileUtils import OsFunctions
from BackEnd.General import Paths


class DBParentClass(unittest.TestCase):
    """Parent class providing DB access and query loading."""

    db_api = None  # class-level attribute if needed
    queries = None

    @classmethod
    def setUpClass(cls):
        """Runs once before all tests to load queries and DB."""
        cls.db_api = DBFactory.get_prod_db_mongo()
        cls.queries = cls._load_all_queries(
            Paths.QA_MONGO_QUERIES,
            Paths.DATA_CLEANUP_MONGO_QUERIES,
            # Add more paths here if needed
        )
        OsFunctions.clear_create_directory(Paths.TESTS_DIR)

    @staticmethod
    def _load_all_queries(*file_paths: str) -> dict:
        """Load and merge multiple JSON files into a single dict."""
        all_queries = {}
        for file_path in file_paths:
            if Path(file_path).exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    queries = json.load(f)
                    all_queries.update(queries)  # merge, later files overwrite duplicates
            else:
                print(f"Warning: Query file {file_path} does not exist.")
        return all_queries

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
        self.db_api.disconnect()