# bs'd
from BackEnd.DataObjects.Enums import SourceContentType
from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.DataPipeline.DB.Collections import CollectionName
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.EntityRelManager import EntityRelManager
from BackEnd.DataPipeline.LMM_api.GeminiLmmCaller import GeminiLmmCaller



class DBPopulateSourceContentAndFaiss(DBParentClass):

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first
        self.lmm_caller = GeminiLmmCaller(api_key="your-api-key-here")
        self.entity_rel_mngr = EntityRelManager(self.db_api)

    def tearDown(self):
        super().tearDown()

        ############################################## Populating FAISS ###############################################

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












