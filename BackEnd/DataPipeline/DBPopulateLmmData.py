# bs'd
import os

from BackEnd.DataObjects.Enums import SourceContentType
from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.DataPipeline.DB.Collections import CollectionName
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.EntityRelManager import EntityRelManager
from BackEnd.DataPipeline.LMM_api.GeminiLmmCaller import GeminiLmmCaller
from BackEnd.FileUtils import LocalPrinter, FileTypeEnum, OsFunctions
from BackEnd.General import Paths


class DBPopulateLmmData(DBParentClass):

    prompt_get_entity_rel_from_passage = """
    Extract all entities and relationships from the following passage of Jewish Tanach.

    Return ONLY valid JSON in this schema:

    {
      "res": {
        "Entities": {
          "Person": [ { "en_name": "" }, ... ],
          "Place": [ { "en_name": "" }, ... ],
          "TribeOfIsrael": [ { "en_name": "" }, ... ],
          "Nation": [ { "en_name": "" }, ... ],
          "Symbol": [ { "en_name": "" }, ... ]
        },
        "Rel": {
          "studiedFrom": [ { "term1": "", "term2": "" }, ... ],
          "siblingWith": [ { "term1": "", "term2": "" }, ... ],
          "childOf": [ { "term1": "", "term2": "" }, ... ],
          "spouseOf": [ { "term1": "", "term2": "" }, ... ],
          "descendantOf": [ { "term1": "", "term2": "" }, ... ],
          "bornIn": [ { "term1": "", "term2": "" }, ... ],
          "diedIn": [ { "term1": "", "term2": "" }, ... ],
          "residedIn": [ { "term1": "", "term2": "" }, ... ],
          "visited": [ { "term1": "", "term2": "" }, ... ],
          "personToTribeOfIsrael": [ { "term1": "", "term2": "" }, ... ],
          "personToNation": [ { "term1": "", "term2": "" }, ... ],
          "EnemyOf": [ { "term1": "", "term2": "" }, ... ],
          "AllyOf": [ { "term1": "", "term2": "" }, ... ],
          "placeToNation": [ { "term1": "", "term2": "" }, ... ],
          "comparedTo": [ { "term1": "", "term2": "" }, ... ],
          "contrastedWith": [ { "term1": "", "term2": "" }, ... ],
          "alias": [ { "term1": "", "term2": "" }, ... ],
          "aliasFromSages": [ { "term1": "", "term2": "" }, ... ]
        }
      }
    }

    Rules:
    1. All lists may contain multiple entries. If a list is empty, omit its key entirely.
    2. Include only entity types and relationship types that appear in the passage.
    3. Any term used in Rel (term1 or term2) must also appear in Entities with the same normalized name.
    4. "en_name" must be normalized (e.g., "Edom" not "Edomite"; "Abraham" not "Abraham's")
    5. Output valid JSON only, with no extra text.
    6. 'studiedFrom' includes anyone who quotes a previous sage.
    7. 

    Relationship typing rules (strict):
    - Person ↔ Person:
      studiedFrom, siblingWith, childOf, spouseOf, descendantOf
    - Person → Place:
      bornIn, diedIn, residedIn, visited
    - Person → TribeOfIsrael:
      personToTribeOfIsrael
    - Person → Nation:
      personToNation
    - Nation ↔ Nation:
      EnemyOf, AllyOf
    - Place → Nation:
      placeToNation
    - Any entity → Symbol:
      comparedTo, contrastedWith
    - Any entity ↔ Any entity (same normalized name allowed):
      alias, aliasFromSages
    - Enforce directional/typing consistency:
      term1 and term2 must match the allowed entity types above, otherwise the relationship must be omitted.
    - TribeOfIsrael entities must be one of the 13 tribes; "Israel" itself should be represented as a Nation.
    """

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first
        self.lmm_caller = GeminiLmmCaller()
        self.entity_rel_mngr = EntityRelManager()

    def tearDown(self):
        super().tearDown()

    ############################################## dummy testing ###############################################

    def test_foo(self):
        prompt = self.prompt_get_entity_rel_from_passage
        OsFunctions.clear_create_directory(Paths.LMM_RESPONSES_OUTPUT_DIR)
        for src_content in self.get_examples_texts():
            response = self.lmm_caller.call(prompt + "\n\n" + src_content.get_clean_en_text())
            path = os.path.join(Paths.LMM_RESPONSES_OUTPUT_DIR, src_content.key.replace(':', ';')).__str__()
            LocalPrinter.print_to_file(src_content.get_clean_en_text() + "\n\n" + response.content, FileTypeEnum.FileType.TXT,
                                       path)
        print(Paths.LMM_RESPONSES_OUTPUT_DIR)

    ############################################## Populating Metadata ###############################################

    def test_populate_source_meta_data(self):
        all_srcs = self.db_api.get_all_src_contents_of_collection(CollectionName.BT)
        src_processed = 0
        num_srcs_to_process = 20

        for src in all_srcs:
            if src_processed >= num_srcs_to_process:
                break

            if self.db_api.is_src_metadata_exist(src.key):
                continue

            analyzed_response = self.lmm_caller.analyze_src(src.content[SourceContentType.EN])
            src_metadata = SourceMetadata(key = src.key, source_type=src.source_type)
            src_metadata.passage_types = analyzed_response.e_passage_types
            src_metadata.summary_en = analyzed_response.summary_en
            src_metadata.summary_heb = analyzed_response.summary_heb

            entity_keys = self.entity_rel_mngr.insert_entity_map(analyzed_response.get_entity_map(), src.get_src_type())
            src_metadata.entities.update(entity_keys)

            rel_keys = self.entity_rel_mngr.insert_rel_map(analyzed_response.get_all_relationships(), src.get_src_type())
            src_metadata.entities.update(rel_keys)

            is_success = self.db_api.insert_or_update_source_metadata(src)
            if is_success:
                src_processed += 1

    def test_populate_entity_meta_data(self):
        pass
        # all_entities = self.db_api.get_all_entities()
        # entities_processed = 0
        # num_ents_to_process = 20
        #
        # for ent in all_entities:
        #     if entities_processed >= num_ents_to_process:
        #         break
        #
        #     if self.db_api.is_entity_processed(ent.key):
        #         continue
        #
        #     # todo...
        #
        #     is_success = 0
        #     if is_success:
        #         entities_processed += 1


    ############################################## helper methods ####################################################
    def get_examples_texts(self):
        res = [
            self.db_api.find_one_source_content(CollectionName.TN, 'TN_Exodus_0_17:8-13'),
            self.db_api.find_one_source_content(CollectionName.TN, 'TN_Deuteronomy_0_1:41-2:1')
        ]
        return res












