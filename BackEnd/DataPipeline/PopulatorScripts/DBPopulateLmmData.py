# bs'd
import os

from BackEnd.DataObjects.Enums import SourceContentType
from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.DataPipeline.DB.Collections import CollectionObjs
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.EntityRelManager import EntityRelManager
from BackEnd.DataPipeline.LMM_api.GeminiLmmCaller import GeminiLmmCaller
from BackEnd.DataPipeline.LMM_api.LmmResponses.AnalyzedEntitiesResponse import AnalyzedEntitiesResponse
from BackEnd.DataPipeline.LMM_api.LmmResponses.RawLmmResponse import RawLmmResponse
from BackEnd.FileUtils import LocalPrinter, FileTypeEnum, OsFunctions
from BackEnd.General import Paths


class DBPopulateLmmData(DBParentClass):

    prompt_get_entity_rel_from_passage = """
    Extract all entities and relationships from the following passage of Jewish Tanach.

    Return ONLY valid JSON in this schema:

    {
    
      "res": {
        "en_summary" : "",
        "heb_summary" : "",
        "passage_types" : [ { "val": "" } , ... ],
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
          "personBelongsToNation": [ { "term1": "", "term2": "" }, ... ],
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
    
GENERAL RULES

1. "en_summary" and "heb_summary" must be 4-10 words.
2. "passage_types" must have at least 1 value
3. "passage_types" can only be 'LAW', 'STORY', 'PHILOSOPHIC', 'GENEALOGY', 'PROPHECY'

ENTITY RULES

1. Include only entities explicitly present in the passage. No inventions or inferences.
2. "en_name" must be normalized (examples: Edom not Edomites, Abraham not Abraham's).
3. Person, Place, and Nation must be proper nouns.
4. TribeOfIsrael includes only these names: Reuben, Simon, Levi, Judah, Issachar, Zebulun, Asher, Gad, Dan, Naphtali, Joseph, Benjamin, Manasseh, Ephraim.
5. Israel cannot be a Person.
6. Symbol is for non-proper-noun metaphors (example: wolf, lamb, rod, girdle).
7. Every term appearing in any relationship must appear first in Entities with the same normalized name.

RELATIONSHIP RULES

1. Include only relationships explicitly stated in the passage. No inferred or implied relationships.
2. Relationship endpoints must match these allowed type pairings exactly:

Person ↔ Person:
studiedFrom, siblingWith, childOf, spouseOf, descendantOf

Person → Place:
bornIn, diedIn, residedIn, visited

Person → TribeOfIsrael:
personToTribeOfIsrael

Person → Nation:
personBelongsToNation

Nation ↔ Nation:
EnemyOf, AllyOf

Place → Nation:
placeToNation

Any entity → Symbol:
comparedTo, contrastedWith

Any entity ↔ Any entity:
alias, aliasFromSages

3. If term1 or term2 does not match the required entity types, OMIT THAT RELATIONSHIP ENTIRELY.
4. term1 cannot equal term2.
5. studiedFrom is only for explicit quotations or learning from an earlier sage.
6. Output must be valid JSON only, with no commentary.

VALIDATION REQUIREMENTS (for correctness)
Before producing JSON, apply these rules:

1. Determine Entities first, only from explicit text. Do not create any relationship yet.
2. For each relationship, term1 and term2 must:
- exactly match an extracted entity's name,
- match the required types for the relationship,
- come from explicit statements in the passage.
If any of these fails, omit the relationship.
3. Do not assume or infer any identity or relationship beyond explicit text.
4. Remove any keys in Entities or Rel that would be empty.

Return only the final JSON.
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

        for src_content in self.get_examples_src_contents():
            # response = self.lmm_caller.call(prompt + "\n\n" + src_content.get_clean_en_text())
            response = RawLmmResponse(success=True, content='foo')
            path = os.path.join(Paths.LMM_RESPONSES_OUTPUT_DIR, src_content.key.replace(':', ';')).__str__()
            LocalPrinter.print_to_file(src_content.__str__() + "\n\n" +
                                       src_content.get_clean_heb_text() + "\n\n" +
                                       # src_content.get_clean_en_text() + "\n\n" +
                                       response.content + "\n\n" +
                                       # "raw en html content:\n" + src_content.get_en_html_content(),
                                       "raw heb html content:\n" + src_content.get_heb_html_content(),
                                       FileTypeEnum.FileType.TXT,
                                       path)
        print(Paths.LMM_RESPONSES_OUTPUT_DIR)

    ############################################## Populating Metadata ###############################################

    def test_populate_source_meta_data(self):
        all_srcs = self.db_api.get_all_src_contents_of_collection(CollectionObjs.BT)
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
    def get_examples_src_contents(self):
        # took sources from file:///C:/Users/U6072661/AppData/Local/Chatblatt/Tests/Questions/fight.html

        key_strs = [
            # amalek, joshua, moshe, etc.
            'TN_Exodus_0_17:8-13',
            # amorites, kadesh, etc.
           'TN_Deuteronomy_0_1:41-2:1',
            # symbols (from az yashir)
            'TN_Exodus_0_15:6-10',
            # small, mostly empty source:
            'TN_Psalms_0_120:1–7',
            # tribes:
            'TN_Isaiah_0_11:1–12:6',
        #     gemara, rabbi studying for other rabbi, etc
            'BT_Eruvin_0_45a:12-19',
        ]
        res = [self.db_api.find_one_source_content(k) for k in key_strs]
        return res












