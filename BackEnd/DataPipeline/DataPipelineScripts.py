import concurrent.futures
import csv
import re
import unittest
import os

import unicodedata
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
from BackEnd.Sources.SourceClasses import SourceContentType


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

        self.db = DBapiMongoDB(uri)
        self.faiss = FaissEngine.FaissEngine(dbapi=self.db) #<- make this lazy inst

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
        self.fetch_and_init_process_sefaria_passages(self.db.insert_source, 10203)

    def test_delete_all_collections(self):
        # dangerous! be careful
        print(self.db.CollectionName)
        # self.db.delete_collection(self.db.CollectionName.BT.value)
        # self.db.delete_collection(self.db.CollectionName.TN.value)
        # self.db.delete_collection(self.db.CollectionName.FS)

    def test_clear_en_clean_content(self):
        print(self.db.CollectionName)
    #     todo complete..

    def fetch_and_init_process_sefaria_passages(self, process_function, start_index):
        ''' includes BT and TN'''

        # 12487 last gemara entry before tanach entry
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
            # self.extract_content_italics
            self.populate_clean_english_content
        ]
        collection_names = [
            self.db.CollectionName.TN.value,
            self.db.CollectionName.BT.value
        ]
        self.process_all_documents(collection_names=collection_names, functions =functions)

        # print(", ".join(sorted(self.tags_seen)))
        # print(", ".join(sorted(self.terms_used)))
        # self.write_glossary_csv(self.terms_used)

    def process_all_documents(self, collection_names, functions):

        # does NOT run multithreaded (safer for serial processing)
        for collection_name in collection_names:
            print(f"Processing collection: {collection_name}")
            documents = self.db.execute_query({'collection': collection_name, 'filter': {}})

            for doc in documents:
                for func in functions:
                    try:
                        func(doc, collection_name)  # Pass both doc and collection if needed
                    except Exception as e:
                        print(f"Error processing doc {doc.get('_id')}: {e}")

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

    def populate_clean_english_content(self, doc, collection_name):
        try:
            enriched = doc.copy()

            # Check that EN content exists
            en_index = SourceContentType.EN.value
            content_list = enriched.get('content', [])
            en_html_content = content_list[en_index] if len(content_list) > en_index else None

            if en_html_content is None:
                print(f"[Warning] Document missing EN content: {enriched.get('key', 'unknown key')}")
                return 0

            # Check that key exists
            doc_key = enriched.get('key')
            if not doc_key:
                print(f"[Error] Document missing 'key' field: {enriched}")
                return 0

            # Clean the English text
            clean_en_content = self.clean_text_for_search(self, en_html_content)

            # Prepare the update dict
            update_dict = {f"content.{SourceContentType.EN_CLEAN.value}": clean_en_content}

            # Update by key
            modified_count = self.db.update_by_key(collection_name, doc_key, update_dict)

            if modified_count == 0:
                print(f"[Info] No document updated for key '{doc_key}' in collection '{collection_name}'")
            return modified_count

        except Exception as e:
            print(f"[Error] Failed to populate clean English content for key '{enriched.get('key', 'unknown')}': {e}")
            return 0

    @staticmethod
    def clean_text_for_search(self, html_content):

        # 1. Remove all HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)

        # 2. Normalize unicode (remove accents etc.)
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

        # 3. Lowercase
        text = text.lower()

        # 4. Remove unwanted characters (keep letters, numbers, and useful punctuation)
        text = re.sub(r"[^a-z0-9\s\.,!?;:'\"()\-\[\]{}]", " ", text)

        # 5. Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

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


    ############################################## Basic Testing with FAISS ###############################################

    def test_basic_faiss_index(self):
        # simple test.. should be replaced..todo
        doc1 = {
            "key": "BT_Bava Batra_0_4a:10-11",
            "content": "The mishna teaches: In a place where it is customary to build a wall of non-chiseled stone, or chiseled stone, or small bricks, or large bricks, they must build the partition with that material. Everything is in accordance with the regional custom. The Gemara asks: What does the word everything serve to add? The Gemara answers: It serves to add a place where it is customary to build a partition out of palm and laurel branches. In such a place, the partition is built from those materials.The mishna teaches: Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally. The Gemara questions the need for this ruling: Isn’t it obvious that this is the case, since both neighbors participated in the construction of the wall? The Gemara answers: No, it is necessary to teach this halakha for a case where the entire wall fell into the domain of one of them. Alternatively, it is necessary in a case where one of them already cleared all the stones into his own domain. Lest you say that the other party should be governed by the principle that the burden of proof rests upon the claimant, that is, if the other party should have to prove that he had been a partner in the construction of the wall, the mishna teaches us that they are presumed to have been partners in the building of the wall, and neither requires further proof."
        }
        doc2 = {
            "key" :" BT_Bava Batra_0_2a:1-5",
            "content": "MISHNA: Partners who wished to make a partition [meḥitza] in a jointly owned courtyard build the wall for the partition in the middle of the courtyard. What is this wall fashioned from? In a place where it is customary to build such a wall with non-chiseled stone [gevil], or chiseled stone [gazit], or small bricks [kefisin], or large bricks [leveinim], they must build the wall with that material. Everything is in accordance with the regional custom.If they build the wall with non-chiseled stone, this partner provides three handbreadths of his portion of the courtyard and that partner provides three handbreadths, since the thickness of such a wall is six handbreadths. If they build the wall with chiseled stone, this partner provides two and a half handbreadths and that partner provides two and a half handbreadths, since such a wall is five handbreadths thick. If they build the wall with small bricks, this one provides two handbreadths and that one provides two handbreadths, since the thickness of such a wall is four handbreadths. If they build with large bricks, this one provides one and a half handbreadths and that one provides one and a half handbreadths, since the thickness of such a wall is three handbreadths. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally.And similarly with regard to a garden, in a place where it is customary to build a partition in the middle of a garden jointly owned by two people, and one of them wishes to build such a partition, the court obligates his neighbor to join in building the partition. But with regard to an expanse of fields [babbika], in a place where it is customary not to build a partition between two people’s fields, and one person wishes to build a partition between his field and that of his neighbor, the court does not obligate his neighbor to build such a partition.Rather, if one person wishes to erect a partition, he must withdraw into his own field and build the partition there. And he makes a border mark on the outer side of the barrier facing his neighbor’s property, indicating that he built the entire structure of his own materials and on his own land. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong only to him, as is indicated by the mark on the wall.Nevertheless, in a place where it is not customary to build a partition between two people’s fields, if they made such a partition with the agreement of the two of them, they build it in the middle, i.e., on the property line, and make a border mark on the one side and on the other side. Therefore, if the wall later falls, the assumption is that the space where the wall stood and the stones belong to both of them, to be divided equally."
        }
        doc3 = {
            "key": "BT_Bava Batra_0_3a:2-14",
            "content": "The Gemara has so far presented one version of the discussion of the mishna. A different version relates the discussion as follows: The Sages initially assumed: What is the meaning of the term meḥitza mentioned in the mishna? A division, not a partition, as it is written: “And the division of [meḥetzat] the congregation was” (Numbers 31:43). According to this interpretation, the mishna means to say: Since they wished to divide the jointly owned courtyard, they build a proper wall in the center even against the will of one of the partners. Apparently, it may be concluded that damage caused by sight is called damage.The Gemara objects to this conclusion: But why not say: What is the meaning of the term meḥitza mentioned in the mishna? It means a partition. This usage would be as we learned in a baraita: Consider the case where a partition of [meḥitzat] a vineyard which separates the vineyard from a field of grain was breached, resulting, if the situation is not rectified, in the grain and grapes becoming items from which deriving benefit is prohibited. The owner of the field of grain may say to the owner of the vineyard: Build a partition between the vineyard and the field of grain. If the owner of the vineyard did so, and the partition was breached again, the owner of the field of grain may say to him again: Build a partition. If the owner of the vineyard neglected to make the necessary repairs and did not properly build a partition between the fields, the grain and grapes are rendered forbidden due to the prohibition of diverse kinds planted in a vineyard, and he is liable for the monetary loss.The Gemara concludes stating the objection: And according to the understanding that the term meḥitza means a partition, one can infer: The reason that they build a wall is that they both wished to make a partition in their jointly owned courtyard. But if they did not both wish to do so, the court does not obligate the reluctant partner to build such a wall, although his neighbor objects to the fact that the partner can see what he is doing in his courtyard. Apparently, it may be concluded that damage caused by sight is not called damage.The Gemara rejects this argument: If so, the words: They build the wall, are imprecise, as the tanna should have said: They build it, since the wall and the partition are one and the same. The Gemara retorts: Rather, what is the meaning of the term meḥitza? A division. If it is so that the term meḥitza means a division, the words: Who wished to make a division, are imprecise, as the tanna should have said: Who wished to divide. The Gemara answers: The phrasing of the mishna is as people commonly say: Come, let us make a division. Consequently, the mishna can also be understood as referring to two people who wished to divide a jointly owned area.The Gemara asks, according to the understanding that meḥitza means division: But if damage caused by sight is called damage, why does the tanna specifically teach that if they wish, they build a wall? Even if they did not both wish to do so, it should also be possible to compel the reluctant party to build a wall between them. Rabbi Asi said that Rabbi Yoḥanan said: Our mishna is referring to a courtyard that is not subject to the halakha of division. Joint owners of a courtyard cannot be compelled to divide the courtyard unless each party will receive at least four square cubits of the courtyard. And therefore, this ruling of the mishna applies only in the case where they both wished to divide the courtyard.The Gemara asks: According to this understanding, what is the tanna teaching us? Is he teaching us that when a courtyard is not subject to the halakha of division, if they nevertheless wished to do so, they divide it? But we already learned this in the latter clause of a different mishna (11a): When do they not divide the courtyard because it is not large enough to compel division? When the joint owners do not both wish to divide it. But when both of them wish to divide it, they divide it even if it is smaller than this, i.e., smaller than four square cubits for each party. The Gemara answers: If we had learned this halakha only from there, I would say that they divide the courtyard even if it is smaller than this by constructing a mere partition of pegs, which does not prevent invasion of privacy. Therefore, the tanna teaches us here in this mishna that if they wish to divide the courtyard they can be compelled to build a proper wall.The Gemara asks: If so, let the tanna teach this mishna and not teach that other mishna, as this mishna teaches more details than the later one. The Gemara answers: It was necessary for the tanna to teach the other mishna to introduce the last clause of that mishna, which states: And jointly owned sacred writings that are contained in a single scroll should not be divided even if both owners wish to do so.The Gemara brings a different version of the previous discussion: And if they wished to divide the courtyard, what of it? What forces them to build the wall? If one of the parties does not wish to build a wall, let him retract. Rav Asi said that Rabbi Yoḥanan said that the mishna is not discussing a case where they merely reached a verbal agreement to divide the courtyard, but rather with a case where each party performed an act of acquisition with the other, confirming their respective commitments. Therefore, neither side can retract.The Gemara asks: Rather than teaching us a case where the courtyard is not subject to the halakha of division, but nevertheless they wished to divide it, let the mishna teach us a case where the courtyard is subject to the halakha of division, even if they did not both wish to divide it. The Gemara answers: Had it taught us only a case where the courtyard is subject to the halakha of division that applies even if they did not both wish to divide it, I would say that in a case where the courtyard is not subject to the halakha of division then even if they both wished to divide it, if one of the parties does not wish to build a proper wall he cannot be compelled to do so. Therefore, the mishna teaches us that he is compelled to participate.The Gemara asks: But how can you say this? Doesn’t the latter clause of the mishna (11a) teach: When do they not divide the courtyard because it is not large enough to compel division? When the joint owners do not both wish to divide it. But when both of them wish to divide it, they divide it even if it is smaller than this. What, is this clause of the mishna not referring to the fact that either one can force the other to build a proper wall? The Gemara answers: No, it is referring to a mere partition of pegs and not to an actual wall.The Gemara asks: If so, let the tanna teach this mishna and not teach that other mishna, as this mishna teaches more details than the later one. The Gemara answers: It was necessary to teach the other mishna for the last clause of that mishna, which states: And jointly owned sacred writings that are contained in a single scroll should not be divided even if both owners wish to do so. This concludes the alternative version of the discussion.The Gemara continues its analysis of the mishna: To what case did you interpret the mishna to be referring? To a case where the courtyard is not subject to the halakha of division. But if there is no halakha of division, then if they wished to divide the courtyard, what of it; how can either one force the other to build a wall? If the parties no longer want to build a wall, let them retract. Rabbi Asi said that Rabbi Yoḥanan said: It is referring to a case where each party performed an act of acquisition with the other, confirming their respective commitments. Therefore, neither party can retract.The Gemara asks: But even if each party performed an act of acquisition with the other, what of it? It is merely a verbal acquisition, meaning there was no actual transfer of property, but only a verbal agreement to act in a certain manner in the future and not a true act of acquisition. The Gemara answers: They performed an act of acquisition with the other with regard to directions, i.e., not only did they verbally agree to divide the courtyard, they also determined which of them would get which part of the courtyard. Consequently, the acquisition related to actual property, a particular plot of land. Rav Ashi said: For example, this one walked through his designated portion and performed an act demonstrating ownership there, and that one walked through his designated portion and performed an act demonstrating ownership there"
        }

        self.faiss.add_documents([doc1, doc2, doc3])
        results = self.faiss.search("custom of building partitions")
        for r in results:
            print(r)
