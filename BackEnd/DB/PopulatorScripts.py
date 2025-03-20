import json
import unittest
import os
from BackEnd.DataFetchers.SefariaFetcher import SefariaFetcher
from BackEnd.FileUtils.JsonWriter import JsonWriter
from BackEnd.General import Paths, Enums, Logger
from BackEnd.FileUtils import OsFunctions, LocalPrinter
import inspect

class PopuplatorScripts(unittest.TestCase):


    def setUp(self):
        """Runs before every test to set up necessary directories."""
        OsFunctions.clear_create_directory(Paths.TESTS_DIR)
        self.logger = Logger.Logger()


    def test_convert_index_from_BSON_to_JSON(self):
        # pre
        self.test_path = Paths.get_test_output_path(inspect.currentframe().f_code.co_name, Enums.FileType.JSON.name)
        # body

        # Define paths
        input_bson_path = r"/mongo_bson_sefaria/passage.bson"
        output_json_path = os.path.join(Paths.TESTS_DIR, "BT_passages_index.json")  # Ensure Paths.TESTS_DIR is defined

        # Convert BSON to JSON
        JsonWriter.bson_to_json(input_bson_path, output_json_path)

    def test_fetch_sefaria_passages(self):
        sefaria_fetcher = SefariaFetcher()

        # Load JSON data from file
        with open(Paths.SEFARIA_INDEX_BT_PASSAGES, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Limit entries
        json_data = json_data[:5]

        # Iterate through the JSON data and fetch texts
        results = {}
        for entry in json_data:
            full_ref = entry["full_ref"]
            print(f"\n\nFetching: {full_ref}\n") #todo change to logger
            results[full_ref] = sefaria_fetcher.fetch_sefaria_passage_as_Source_from_reference(full_ref)

        print(results)

