# import unittest
#
# from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
# from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB
# from BackEnd.DataPipeline.DataFetchers.SefariaFetcher import SefariaFetcher
# from BackEnd.General import Paths, Enums, Logger
# from BackEnd.FileUtils import OsFunctions, LocalPrinter
# import inspect
#
# class TestExample(unittest.TestCase):
#
#     test_path = None
#
#     def setUp(self):
#         """Runs before every test to set up necessary directories."""
#         OsFunctions.clear_create_directory(Paths.TESTS_DIR)
#         self.logger = Logger.Logger()
#
#
#     # def test_basic_json_print(self):
#     #     # pre
#     #     self.test_path = Paths.get_test_output_path(inspect.currentframe().f_code.co_name, Enums.FileType.JSON.name)
#     #     # body
#     #     sefaria_fetcher = SefariaFetcher()
#     #     json_res = sefaria_fetcher.fetch_talmud_daf_as_RAW('Niddah', '54a')
#     #     # json_res = sefaria_fetcher.fetch_talmud_daf_range('Berakhot', '2a', '4a')
#     #
#     #     LocalPrinter.print_to_file(json_res, Enums.FileType.JSON, self.test_path)
#     #     self.logger.log(f"printed to {self.test_path}")
#
#     def test_foo(self):
#         # reserved for any small test
#         pass
#
# ###################################################################
#
# if __name__ == "__main__":
#     unittest.main()
