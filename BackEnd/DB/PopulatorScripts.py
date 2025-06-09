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
        uri = f"mongodb+srv://{username}:{password}@chatblatt.sdqpvk2.mongodb.net/?retryWrites=true&w=majority&appName=ChatBlatt"

        # Initialize the MongoDB database interface with the connection string
        self.db = DBapiMongoDB(uri)

        # self.logger = Logger.Logger()
        # self.logger.mute()

    def tearDown(self):
        """Runs after every test to clean up resources."""
        # Disconnect from the database
        self.db.disconnect()

    def test_populate_BT_and_TN_to_db(self):
        self.fetch_and_process_sefaria_passages(self.db.insert_source)

    def test_delete_collection(self):
        self.db.delete_collection(self.db.BT)

    def fetch_and_process_sefaria_passages(self, process_function):
        ''' includes BT and TN'''
        sefaria_fetcher = SefariaFetcher()

        json_data = OsFunctions.open_json_file(Paths.SEFARIA_INDEX_BT_PASSAGES)
        if json_data is None:
            return

        # Limit entries
        start_index = 12487
        json_data = json_data[start_index:]
        book_name_set = set()

        # Use ThreadPoolExecutor to parallelize the fetching of passages
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(sefaria_fetcher.fetch_sefaria_passage_as_Source_from_data, ref): ref for ref
                       in json_data}

            for future in concurrent.futures.as_completed(futures):

                ref = futures[future]
                try:
                    result = future.result()
                    errors = result.is_valid_else_get_error_list()
                    if len(errors) > 0:
                        print(f"empty source! {ref} {start_index}")
                        raise InvalidDataError(ref, start_index, errors)

                    start_index += 1
                    if result.book not in book_name_set:
                        book_name_set.add(result.book)
                        print(f"{result.book} -- {SystemFunctions.get_ts()} -- {start_index}")

                    process_function(result, ref, start_index)

                except Exception as e:
                    print(f"Error fetching reference {ref} index {start_index}: {e}")
                    break

        print(f"finished - {SystemFunctions.get_ts()}")

    def test_connect_to_db(self):

        test_collection_name = self.db.BT

        # Insert example data into collection
        data = {'key': 'example_key', 'content': 'This is the content of the Talmud passage.'}
        doc_id = self.db.insert(test_collection_name, data)  # Specify collection name
        print(f"Inserted document ID: {doc_id}")

        # Query data
        query_results = self.db.execute_query({'collection': test_collection_name, 'filter': {'key': 'example_key'}})
        print(f"Query results: {query_results}")

        # Update data
        updated_rows = self.db.update(test_collection_name, {'key': 'example_key'},
                                 {'content': 'Updated content of the Talmud passage.'})
        print(f"Updated {updated_rows} rows.")

        # Delete data
        deleted_rows = self.db.delete_instance(test_collection_name, {'key': 'example_key'})
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