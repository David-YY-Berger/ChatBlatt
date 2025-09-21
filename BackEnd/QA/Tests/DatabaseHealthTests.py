import unittest

from BackEnd.DataPipeline.DB.DBFactory import DBFactory
from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB


class DatabaseHealthTests(unittest.TestCase):

    db_api = DBFactory.get_prod_db_mongo()

    def setUp(self):
        """Runs before every test to set up necessary directories."""
        pass

    def test_foo(self):
        # reserved for any small test
        pass

    def test_valid_sources(self):
        # self.db_api.execute_raw_query()
        pass

    def test_valid_num_sources(self):
        pass

###################################################################

if __name__ == "__main__":
    unittest.main()