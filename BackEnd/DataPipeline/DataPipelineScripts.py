import concurrent.futures
import csv
import re
import unittest
import os

from dotenv import load_dotenv

from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB
from BackEnd.DataPipeline.DataFetchers.SefariaFetcher import SefariaFetcher
from BackEnd.DataPipeline.FAISS_api import FaissEngine
from BackEnd.FileUtils.JsonWriter import JsonWriter
from BackEnd.General import Paths, Enums, SystemFunctions
from BackEnd.FileUtils import OsFunctions
import inspect
from bs4 import BeautifulSoup

from BackEnd.General.exceptions import InvalidDataError
from BackEnd.Objects.SourceClasses import SourceContentType


class DBScripts(unittest.TestCase):


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

        # sets for processing over data.
        self.tags_seen = set()
        self.terms_used = set()


        # self.logger = Logger.Logger()
        # self.logger.mute()

    def tearDown(self):
        """Runs after every test to clean up resources."""
        # Disconnect from the database
        self.db.disconnect()

    ############################################ Populator Scripts ######################################################

    def test_populate_BT_and_TN_to_db(self):
        self.fetch_and_process_sefaria_passages(self.db.insert_source)

    def test_delete_all_collections(self):
        self.db.delete_collection(self.db.CollectionName.BT.value)
        self.db.delete_collection(self.db.CollectionName.TN.value)

    def fetch_and_process_sefaria_passages(self, process_function):
        ''' includes BT and TN'''

        # 12487 last gemara entry before tanach entry

        start_index = 0
        references = self.load_references(start_index)
        book_name_set = set()
        sefaria_fetcher = SefariaFetcher()

        # Use ThreadPoolExecutor to parallelize the fetching of passages
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit all fetch tasks to the executor
            futures = {
                executor.submit(
                    sefaria_fetcher.fetch_sefaria_passage_as_Source_from_data, ref
                ): ref
                for ref in references
            }

            for completed_fetch in concurrent.futures.as_completed(futures):

                ref = futures[completed_fetch]
                try:
                    source = completed_fetch.result()
                    errors = source.is_valid_else_get_error_list()
                    if len(errors) > 0:
                        print(f"empty source! {ref} {start_index}")
                        raise InvalidDataError(ref, start_index, errors)

                    start_index += 1
                    if source.book not in book_name_set:
                        book_name_set.add(source.book)
                        print(f"{source.book} -- {SystemFunctions.get_ts()} -- {start_index}")

                    process_function(source, ref, start_index)

                except Exception as e:
                    print(f"Error fetching reference {ref} index {start_index}: {e}")
                    break

        print(f"finished - {SystemFunctions.get_ts()}")

    def test_connect_to_db(self):

        # test_collection_name = self.db.BT
        test_collection_name = self.db.CollectionName.TN.value

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

    ############################################ Processing Scripts ####################################################

    def test_process(self):
        functions = [
            # self.extract_tag_types,
            self.extract_content_italics
        ]
        collection_names = [
            self.db.CollectionName.TN.value,
            self.db.CollectionName.BT.value
        ]
        self.process_all_documents(collection_names=collection_names, functions =functions)

        # print(", ".join(sorted(self.tags_seen)))
        # print(", ".join(sorted(self.terms_used)))
        self.write_glossary_csv(self.terms_used)

    def process_all_documents(self, collection_names, functions):

        for collection_name in collection_names:
            print(f"Processing collection: {collection_name}")
            documents = self.db.execute_query({'collection': collection_name, 'filter': {}})

            for doc in documents:
                for func in functions:
                    try:
                        func(doc, collection_name)  # Pass both doc and collection if needed
                    except Exception as e:
                        print(f"Error processing doc {doc.get('_id')}: {e}")

    def extract_tag_types(self, doc, collection):
        enriched = doc.copy()
        english_content = enriched['content'][SourceContentType.EN.value]  # this is your HTML string

        # Use regex to find all tag types
        tags = re.findall(r'</?([a-zA-Z0-9]+)', english_content)

        # Add only unique tag names to the set
        for tag in tags:
            self.tags_seen.add(tag.lower())

    def extract_content_italics(self, doc, collection):
        enriched = doc.copy()
        english_content = enriched['content'][SourceContentType.EN.value]  # HTML string

        soup = BeautifulSoup(english_content, 'html.parser')
        italic_elements = soup.find_all('i')

        for elem in italic_elements:
            text = elem.get_text(strip=True)
            if text:
                self.terms_used.add(text)



    ############################################ Helper Functions ######################################################
    @staticmethod
    def load_references(start_index = 0):
        references = OsFunctions.open_json_file(Paths.SEFARIA_INDEX_BT_PASSAGES)
        if references is None:
            return None

        return references[start_index:]

    ############################################# One time use (upon DB reset) ############################################################

    def test_convert_index_from_BSON_to_JSON(self):
        # pre
        self.test_path = Paths.get_test_output_path(inspect.currentframe().f_code.co_name, Enums.FileType.JSON.name)
        # body

        # Define paths
        input_bson_path = r"/mongo_bson_sefaria/passage.bson"
        output_json_path = os.path.join(Paths.TESTS_DIR, "BT_passages_index.json")  # Ensure Paths.TESTS_DIR is defined

        # Convert BSON to JSON
        JsonWriter.bson_to_json(input_bson_path, output_json_path)

    @staticmethod
    def write_glossary_csv(english_terms):
        with open(Paths.GLOSSARY_TEMP, mode="w", newline='', encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["term_en", "term_heb", "is_a_term", "def"])

            for term in sorted(english_terms):
                writer.writerow([term, "", "", ""])

        print('printed to ' + Paths.GLOSSARY_TEMP)