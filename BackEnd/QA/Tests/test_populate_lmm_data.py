# bs'd
from BackEnd.DataPipeline.DBParentClass import DBParentClass
from BackEnd.DataPipeline.LMM_api.GeminiLmmCaller import GeminiLmmCaller


class TestsForPopulateLmmData(DBParentClass):

    def setUp(self):
        super().setUp()
        self.lmm_caller = GeminiLmmCaller()

    def tearDown(self):
        pass

    def test_simple_lmm_call(self):
        assert (False)
        # make sure you dont call LMM for no reason...

        res = self.lmm_caller.call("foo")
        assert (res.content.__contains__("foo"))
