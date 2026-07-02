import csv
import os
import unittest
from typing import List

from backend.file_utils.HtmlWriter import HtmlWriter
from backend.common import Paths
from backend.file_utils import OsFunctions
from backend_pipeline.file_utils_pipeline import LocalPrinter
from backend.file_utils.FileTypeEnum import FileType

from backend_pipeline.QA.Objects.QueryRow import QueryRow
from backend.app.SearchHandler import SearchHandler
from backend.models_db.Enums import SourceType


class QuerysFromCSVTests(unittest.TestCase):

    def setUp(self):
        super().setUp()
        OsFunctions.clear_create_directory(Paths.QUESTIONS_OUTPUT_DIR)
        self.qaHandler = SearchHandler()
        self.htmlWriter = HtmlWriter()
        # self.logger = Logger.Logger()


    # def test_foo(self):
    #     # reserved for any small test
    #     pass


############################################# 1. Basic Tests ####################################################
    def test_print_query_from_csv(self):
        query_rows = self.get_BT_live_query_from_csv()
        for q in query_rows:
            real_q = q.to_query_from_user(SourceType.BT)

            # when zscalar on, uncomment this line:
            real_q.free_text_similarity = ''

            ans = self.qaHandler.get_full_answer(real_q)
            html_ans = self.htmlWriter.get_full_html(ans)
            path = os.path.join(Paths.QUESTIONS_OUTPUT_DIR, q.query_name)
            LocalPrinter.print_to_file(html_ans, FileType.HTML, path)


############################################# Helper Functions ####################################################

    def read_csv_to_objects(self, file_path: str) -> List[QueryRow]:
        rows: List[QueryRow] = []
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                clean_row = {}
                for k, v in row.items():
                    if k is None or k.strip() == "":
                        continue  # skip empty headers

                    key = k.strip()  # keep exact case to match dataclass
                    v = (v or "").strip()

                    # numeric fields
                    if key in {"BT", "JT", "RM", "TN", "MS", "max_sources"}:
                        clean_row[key] = int(v) if v else None
                    # entity/NER fields as list
                    elif key in {"entities", "ners"}:
                        clean_row[key] = [x.strip() for x in v.split(",")] if v else []
                    # string fields
                    elif key in {"query_name", "query_content"}:
                        clean_row[key] = v or None

                rows.append(QueryRow(**clean_row))
        return rows


    def get_BT_live_query_from_csv(self) -> List[QueryRow]:
        all_q_from_csv = self.read_csv_to_objects(Paths.QA1_PATH)
        return [
            q for q in all_q_from_csv
            if q.BT == 1 and q.query_content is not None and q.query_content.strip() != ""
        ]

#######################################################################################################################

if __name__ == "__main__":
    unittest.main()
