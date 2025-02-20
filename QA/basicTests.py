import unittest
import os
import shutil
from DataFetchers.SefariaFetcher import SefariaFetcher
from General import Paths, Enums, Logger
from FileUtils import LocalPrinter
import inspect

class TestExample(unittest.TestCase):

    test_path = None

    def setUp(self):
        """Runs before every test to set up necessary directories."""
        self.clear_create_directory(Paths.TESTS_DIR)
        self.logger = Logger.Logger()


    def test_basic_json_print(self):
        # pre
        self.test_path = Paths.get_test_output_path(inspect.currentframe().f_code.co_name, Enums.FileType.JSON.name)
        # body
        json_res = SefariaFetcher.fetch_talmud_daf('Berakhot', '2a')

        LocalPrinter.print_to_file(json_res, Enums.FileType.JSON, self.test_path)
        self.logger.log(f"printed to {self.test_path}")




    def clear_create_directory(self, dir_path):
        """Deletes all files and subdirectories in the given directory."""
        if os.path.exists(dir_path):
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)  # Delete file
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)  # Delete directory
                    print(f"Deleted: {item_path}")
                except Exception as e:
                    print(f"Error deleting {item_path}: {e}")
        else:
            print(f"Directory does not exist: {dir_path}")

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)


if __name__ == "__main__":
    unittest.main()
