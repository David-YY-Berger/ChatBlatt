import concurrent.futures
import csv
import re
import unittest
import os

import unicodedata
from bson import ObjectId
from dotenv import load_dotenv

from BackEnd.DataObjects import Enums
from BackEnd.DataPipeline.DB.Collections import CollectionName
from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.DataFetchers.SefariaFetcher import SefariaFetcher
from BackEnd.FileUtils.JsonWriter import JsonWriter
from BackEnd.General import Paths, SystemFunctions, miscFuncs
from BackEnd.FileUtils import OsFunctions, FileTypeEnum
import inspect
from bs4 import BeautifulSoup

from BackEnd.General.exceptions import InvalidDataError
from BackEnd.DataObjects.Enums import SourceContentType


class DBPopulateSourceContent(DBParentClass):

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first

        # sets for processing Source Content.
        self.tags_seen = set()
        self.terms_used = set()

        # self.logger = Logger.Logger()
        # self.logger.mute()

    def tearDown(self):
        super().tearDown()

    ############################################ Populator Scripts ######################################################

    def test_populate_BT_and_TN_to_db(self):
        self.fetch_and_init_process_sefaria_passages(self.db_api.insert_source, 0)

    def test_delete_all_collections(self):
        # dangerous! be careful
        pass
        # self.db.delete_collection(CollectionName.BT.name)
        # self.db.delete_collection(CollectionName.TN.name)
        # self.db.delete_collection(CollectionName.FS)

    def fetch_and_init_process_sefaria_passages(self, process_function, start_index):
        ''' includes BT and TN'''

        # 12487 last gemara entry before tanach entry
        references = self.load_references_from_local_json(start_index)
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
                    source_content = completed_fetch.result()
                    errors = source_content.is_valid_else_get_error_list()
                    if len(errors) > 0:
                        print(f"empty source! {ref} {start_index}")
                        raise InvalidDataError(ref, start_index, errors)

                    start_index += 1
                    if source_content.get_book() not in book_name_set:
                        book_name_set.add(source_content.get_book())
                        print(f"{source_content.get_book()} -- {SystemFunctions.get_ts()} -- {start_index}")

                    process_function(source_content, ref, start_index)

                except Exception as e:
                    print(f"Error fetching reference {ref} index {start_index}: {e}")
                    break

        print(f"finished - {SystemFunctions.get_ts()}")

    ############################################ Processing Scripts ####################################################

    def test_process(self):
        functions = [
            # self.extract_tag_types,
            # self.extract_content_italics,
            # self.remove_all_clean_english_content,
            # self.populate_clean_english_content,
        ]

        collections = [
            # CollectionName.TN,
            # CollectionName.BT,
        ]

        self.process_all_documents(collections=collections, functions=functions)

        # print(", ".join(sorted(self.tags_seen)))
        # print(", ".join(sorted(self.terms_used)))
        # self.write_glossary_csv(self.terms_used)

    def process_all_documents(self, collections, functions):
        """
        Iterate over documents in given collections and apply functions sequentially.
        collections: list of Collection objects (e.g., [CollectionName.BT, CollectionName.FS])
        functions: list of callables that take (doc, collection)
        """
        for collection in collections:
            print(f"Processing collection: {collection.name}")

            documents = self.db_api.execute_raw_query({
                "collection": collection,
                "filter": {}
            })

            for doc in documents:
                for func in functions:
                    try:
                        func(doc, collection)
                    except Exception as e:
                        print(f"Error processing doc {doc.get('_id')}: {e}")

    # -------------------------------------------

    def extract_tag_types(self, doc, collection_name):
        enriched = doc.copy()
        english_content = enriched['content'][SourceContentType.EN.value]  # this is your HTML string

        # Use regex to find all tag types
        tags = re.findall(r'</?([a-zA-Z0-9]+)', english_content)

        # Add only unique tag names to the set
        for tag in tags:
            self.tags_seen.add(tag.lower())

    def extract_content_italics(self, doc, collection_name):
        enriched = doc.copy()
        english_content = enriched['content'][SourceContentType.EN.value]  # HTML string

        soup = BeautifulSoup(english_content, 'html.parser')
        italic_elements = soup.find_all('i')

        for elem in italic_elements:
            text = elem.get_text(strip=True)
            if text:
                self.terms_used.add(text)

    def remove_all_clean_english_content(self, doc, collection_name) -> int:
        return self.db_api.update_doc_field(
            doc,
            collection_name,
            {f"content.{SourceContentType.EN_CLEAN.value}": None},
            action_desc="clean EN removal"
        )

    def DO_NOT_USE_populate_clean_english_content(self, doc, collection_name) -> int:

        # we no longer save the clean content, only save the html. but keeping this func anyway

        try:
            enriched = doc.copy()

            # Check that EN content exists
            en_index = SourceContentType.EN.value
            content_list = enriched.get('content', [])
            en_html_content = content_list[en_index] if len(content_list) > en_index else None

            if en_html_content is None:
                print(f"[Warning] Document missing EN content: {enriched.get('key', 'unknown key')}")
                return 0

            # Clean the English text
            clean_en_content = miscFuncs.clean_en_text_from_html_tags(en_html_content)

            # Update with cleaned content
            return self.db_api.update_doc_field(
                enriched,
                collection_name,
                {f"content.{SourceContentType.EN_CLEAN.name}": clean_en_content},
                action_desc="clean EN populate"
            )

        except Exception as e:
            print(f"[Error] Failed to populate clean English content for key '{doc.get('key', 'unknown')}': {e}")
            return 0


    ############################################ Helper Functions ######################################################
    @staticmethod
    def load_references_from_local_json(start_index = 0):
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


    ############################################## Data Clean up functions ##############################################
    def test_remove_3rd_col_of_content(self):
        # Retrieve the query template
        query = self.get_query("remove_third_content_element")

        try:
            # Execute the query on the __ collection
            # Only documents matching the filter will be updated
            updated_count = self.db_api.execute_query_with_collection(
                query=query,
                collection=CollectionName.BT
            )

            print(f"Updated {len(updated_count)} documents (skipped those without a 3rd element).")
            return updated_count

        except Exception as e:
            print(f"Failed to remove 3rd content element: {e}")
            return 0

    def test_remove_3rd_col_of_content_test(self):

        document_id = ObjectId("68a571fce3ce6b49e57bb1be")

        # Retrieve the test query template
        query = self.get_query("remove_third_content_element_test")

        if not query:
            print("Query 'remove_third_content_element_test' not found.")
            return 0

        # Set the document _id dynamically
        query = query.copy()
        query["filter"]["_id"] = document_id

        try:
            # Execute the query on the TN collection
            updated_count = self.db_api.execute_query_with_collection(
                query=query,
                collection=CollectionName.TN
            )

            print(f"Updated {updated_count} document(s).")
            return updated_count

        except Exception as e:
            print(f"Failed to remove 3rd content element: {e}")
            return 0


