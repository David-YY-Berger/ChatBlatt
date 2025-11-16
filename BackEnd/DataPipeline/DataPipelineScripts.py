import concurrent.futures
import csv
import re
import unittest
import os

import unicodedata
from bson import ObjectId
from dotenv import load_dotenv

from BackEnd.DataObjects import Enums
from BackEnd.DataPipeline.DB.Collection import CollectionName
from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.DataFetchers.SefariaFetcher import SefariaFetcher
from BackEnd.DataPipeline.FAISS_api import FaissEngine
from BackEnd.FileUtils.JsonWriter import JsonWriter
from BackEnd.General import Paths, SystemFunctions, miscFuncs
from BackEnd.FileUtils import OsFunctions, FileTypeEnum
import inspect
from bs4 import BeautifulSoup

from BackEnd.General.exceptions import InvalidDataError
from BackEnd.DataObjects.Enums import SourceContentType


class DataPipelineScripts(DBParentClass):

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first

        OsFunctions.clear_create_directory(Paths.TESTS_DIR)
        load_dotenv()

        self.faiss = FaissEngine.FaissEngine(dbapi=self.db_api)

        # sets for processing over data.
        self.tags_seen = set()
        self.terms_used = set()


        # self.logger = Logger.Logger()
        # self.logger.mute()

    def tearDown(self):
        """Runs after every test to clean up resources."""
        # Disconnect from the database
        self.db_api.disconnect()

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

    def populate_clean_english_content(self, doc, collection_name) -> int:
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
            clean_en_content = miscFuncs.clean_text_for_search(en_html_content)

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


    ############################################## Populating FAISS ###############################################

    def test_populate_faiss_index(self):
        """
        very slow function (on BT, ran for 3.5 hrs till failed), but works well. could be improved, but not worth it, it only needs to run once.
        must NOT interrupt in the middle... then you must delete faiss_data and rerun all collections all over again..
        very possible for mongo connection to be broken.. best to somehow mark exactly which passages where added to FAISS and which were not.
        """
        # doc1 = {
        #     "key": "BT_Bava Batra_0_4a:10-11",
        #     "content": "The mishna teaches: In a place where it is customary to build a wall of non-chiseled stone, or chiseled stone, or small bricks, or large bricks, they must build the partition with that material. Everything is in accordance with the regional custom. The Gemara asks: What does the word everything serve to add? The Gemara answers: It serves to add a place where it is customary to build a partition out of palm and laurel branches. In such a place, the partition is built from those materials.The mishna teaches: Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally. The Gemara questions the need for this ruling: Isn’t it obvious that this is the case, since both neighbors participated in the construction of the wall? The Gemara answers: No, it is necessary to teach this halakha for a case where the entire wall fell into the domain of one of them. Alternatively, it is necessary in a case where one of them already cleared all the stones into his own domain. Lest you say that the other party should be governed by the principle that the burden of proof rests upon the claimant, that is, if the other party should have to prove that he had been a partner in the construction of the wall, the mishna teaches us that they are presumed to have been partners in the building of the wall, and neither requires further proof."
        # }
        # doc2 = {
        #     "key" :" BT_Bava Batra_0_2a:1-5",
        #     "content": "MISHNA: Partners who wished to make a partition [meḥitza] in a jointly owned courtyard build the wall for the partition in the middle of the courtyard. What is this wall fashioned from? In a place where it is customary to build such a wall with non-chiseled stone [gevil], or chiseled stone [gazit], or small bricks [kefisin], or large bricks [leveinim], they must build the wall with that material. Everything is in accordance with the regional custom.If they build the wall with non-chiseled stone, this partner provides three handbreadths of his portion of the courtyard and that partner provides three handbreadths, since the thickness of such a wall is six handbreadths. If they build the wall with chiseled stone, this partner provides two and a half handbreadths and that partner provides two and a half handbreadths, since such a wall is five handbreadths thick. If they build the wall with small bricks, this one provides two handbreadths and that one provides two handbreadths, since the thickness of such a wall is four handbreadths. If they build with large bricks, this one provides one and a half handbreadths and that one provides one and a half handbreadths, since the thickness of such a wall is three handbreadths. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally.And similarly with regard to a garden, in a place where it is customary to build a partition in the middle of a garden jointly owned by two people, and one of them wishes to build such a partition, the court obligates his neighbor to join in building the partition. But with regard to an expanse of fields [babbika], in a place where it is customary not to build a partition between two people’s fields, and one person wishes to build a partition between his field and that of his neighbor, the court does not obligate his neighbor to build such a partition.Rather, if one person wishes to erect a partition, he must withdraw into his own field and build the partition there. And he makes a border mark on the outer side of the barrier facing his neighbor’s property, indicating that he built the entire structure of his own materials and on his own land. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong only to him, as is indicated by the mark on the wall.Nevertheless, in a place where it is not customary to build a partition between two people’s fields, if they made such a partition with the agreement of the two of them, they build it in the middle, i.e., on the property line, and make a border mark on the one side and on the other side. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally."
        # }
        # self.faiss.add_documents([doc1, doc2])
        # all_srcs = self.db_api.get_all_source_contents(CollectionName.BT)

        all_srcs = self.db_api.get_all_source_contents(CollectionName.BT)
        # must put here ^^ every collection separately...
        print(f"{len(all_srcs)} sources found")
        for src in all_srcs:
            cleaned_content = miscFuncs.clean_text_for_search(src.content[SourceContentType.EN.value])
            self.faiss.add_documents([
                {
                    "key": src.key,
                    "content": cleaned_content,
                }
            ])

        results = self.faiss.search("leading the battle", 20) # just to show that it works...
        for r in results:
            print(r)

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


