# bs'd
from BackEnd.DataObjects.Enums import SourceContentType
from BackEnd.DataPipeline.DB.Collections import CollectionName
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.LMM_api.GeminiLmmCaller import GeminiLmmCaller



class DBPopulateSourceContentAndFaiss(DBParentClass):

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first
        self.lmm_caller = GeminiLmmCaller(api_key="your-api-key-here")

    def tearDown(self):
        super().tearDown()

        ############################################## Populating FAISS ###############################################

    def test_populate_lmm_data(self):
        foo = 1