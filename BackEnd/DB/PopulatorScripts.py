import concurrent.futures
import json
import unittest
import os

from dotenv import load_dotenv

from BackEnd.DB.DBapiMongoDB import DBapiMongoDB
from BackEnd.DataFetchers.SefariaFetcher import SefariaFetcher
from BackEnd.FileUtils.JsonWriter import JsonWriter
from BackEnd.General import Paths, Enums, Logger, SystemFunctions
from BackEnd.FileUtils import OsFunctions, LocalPrinter
import inspect

from BackEnd.General.exceptions import InvalidDataError


class PopuplatorScripts(unittest.TestCase):


    def setUp(self):
        """Runs before every test to set up necessary directories."""
        OsFunctions.clear_create_directory(Paths.TESTS_DIR)
        load_dotenv()

        # Retrieve the database username and password from environment variables
        username = os.getenv('DB_BT_USERNAME')
        password = os.getenv('DB_BT_PASSWORD')

        # MongoDB URI with password inserted
        uri = f"mongodb+srv://{username}:{password}@babylonian-talmud.qoltj.mongodb.net/?appName=Babylonian-Talmud"

        # Initialize the MongoDB database interface with the connection string
        self.db = DBapiMongoDB(uri)

        # self.logger = Logger.Logger()
        # self.logger.mute()

    def tearDown(self):
        """Runs after every test to clean up resources."""
        # Disconnect from the database
        self.db.disconnect()

    def test_populate_BT_to_db(self):
        self.fetch_and_process_sefaria_BT_passages(self.db.insert_source)

    def test_delete_collection(self):
        self.db.delete_all('en-sources')

    def fetch_and_process_sefaria_BT_passages(self, process_function):
        # todo refactor to include tanach..
        sefaria_fetcher = SefariaFetcher()

        json_data = OsFunctions.open_json_file(Paths.SEFARIA_INDEX_BT_PASSAGES)
        if json_data is None:
            return

        # Limit entries
        start_index = 0
        json_data = json_data[start_index:]
        tractate_set = set()

        # Prepare the list of references to fetch
        references = [entry["full_ref"] for entry in json_data if entry["type"] in ("Mishnah", "Sugya")]
        # (there is also 'Biblical-story')

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
                        raise InvalidDataError(ref, start_index, errors)

                    start_index += 1
                    if result.book not in tractate_set:
                        tractate_set.add(result.book)
                        print(f"{result.book} -- {SystemFunctions.get_ts()} -- {start_index}")

                    process_function(result, ref, start_index)

                except Exception as e:
                    print(f"Error fetching reference {ref} index {start_index}: {e}")
                    break

        print(f"finished - {SystemFunctions.get_ts()}")

    def connect_to_db(self):


        # Insert some data into the 'en-sources' collection
        data = {'key': 'example_key', 'content': 'This is the content of the Talmud passage.'}
        doc_id = self.db.insert('en-sources', data)  # Specify collection name
        print(f"Inserted document ID: {doc_id}")

        # Query data
        query_results = self.db.execute_query({'collection': 'en-sources', 'filter': {'key': 'example_key'}})
        print(f"Query results: {query_results}")

        # Update data
        updated_rows = self.db.update('en-sources', {'key': 'example_key'},
                                 {'content': 'Updated content of the Talmud passage.'})
        print(f"Updated {updated_rows} rows.")

        # Delete data
        deleted_rows = self.db.delete('en-sources', {'key': 'example_key'})
        print(f"Deleted {deleted_rows} rows.")


    ############################################# rarely used ############################################################

    def test_convert_index_from_BSON_to_JSON(self):
        # pre
        self.test_path = Paths.get_test_output_path(inspect.currentframe().f_code.co_name, Enums.FileType.JSON.name)
        # body

        # Define paths
        input_bson_path = r"/mongo_bson_sefaria/passage.bson"
        output_json_path = os.path.join(Paths.TESTS_DIR, "BT_passages_index.json")  # Ensure Paths.TESTS_DIR is defined

        # Convert BSON to JSON
        JsonWriter.bson_to_json(input_bson_path, output_json_path)