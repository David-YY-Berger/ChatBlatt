# bs'd
from BackEnd.DataPipeline.DBScriptParentClass import DBParentClass


class TestsForPopulateLmmData(DBParentClass):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass

    def test_simple_lmm_call(self):
        pass
        # assert (False)
        # make sure you dont call LMM for no reason...

        # res = self.lmm_caller.call("foo")
        # assert (res.content.__contains__("foo"))
