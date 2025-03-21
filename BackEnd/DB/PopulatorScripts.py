import concurrent.futures
import json
import unittest
import os
from BackEnd.DataFetchers.SefariaFetcher import SefariaFetcher
from BackEnd.FileUtils.JsonWriter import JsonWriter
from BackEnd.General import Paths, Enums, Logger, SystemFunctions
from BackEnd.FileUtils import OsFunctions, LocalPrinter
import inspect

class PopuplatorScripts(unittest.TestCase):


    def setUp(self):
        """Runs before every test to set up necessary directories."""
        OsFunctions.clear_create_directory(Paths.TESTS_DIR)
        # self.logger = Logger.Logger()
        # self.logger.mute()


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
        start_index = 0
        json_data = json_data[start_index:]
        tractate_set = set()

        # Prepare the list of references to fetch
        references = [entry["full_ref"] for entry in json_data]

        # Use ThreadPoolExecutor to parallelize the fetching of passages
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(sefaria_fetcher.fetch_sefaria_passage_as_Source_from_reference, ref): ref for ref
                       in references}

            for future in concurrent.futures.as_completed(futures):
                ref = futures[future]
                try:
                    result = future.result()
                    errors = result.is_valid_else_get_error_list()
                    if len(errors) > 0:
                        print(f"empty source! {ref} {start_index}")

                    start_index += 1
                    if result.book not in tractate_set:
                        tractate_set.add(result.book)
                        print(f"{result.book} -- {SystemFunctions.get_ts()} -- {start_index}")

                except Exception as e:
                    print(f"Error fetching reference {ref} index {start_index}: {e}")
                    break

        print(f"finished - {SystemFunctions.get_ts()}")

