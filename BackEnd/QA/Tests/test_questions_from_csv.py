import csv
import os
import unittest
from typing import List

from BackEnd.FileUtils.HtmlWriter import HtmlWriter
from BackEnd.General import Paths
from BackEnd.FileUtils import OsFunctions, LocalPrinter
from BackEnd.FileUtils.FileTypeEnum import FileType

from BackEnd.QA.Objects.QuestionRow import QuestionRow
from BackEnd.Main.SearchHandler import SearchHandler
from BackEnd.DataObjects.Enums import SourceType


class QuestionsFromCSVTests(unittest.TestCase):

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
    def test_print_questions_from_csv(self):
        question_rows = self.get_BT_live_questions_from_csv()
        for q in question_rows:
            real_q = q.to_question_from_user(SourceType.BT.name)
            ans = self.qaHandler.get_full_answer(real_q)
            html_ans = self.htmlWriter.get_full_html(ans)
            path = os.path.join(Paths.QUESTIONS_OUTPUT_DIR, q.question_name)
            LocalPrinter.print_to_file(html_ans, FileType.HTML, path)


############################################# Helper Functions ####################################################

    def read_csv_to_objects(self, file_path: str) -> List[QuestionRow]:
        rows: List[QuestionRow] = []
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
                    elif key in {"question_name", "question_content"}:
                        clean_row[key] = v or None

                rows.append(QuestionRow(**clean_row))
        return rows


    def get_BT_live_questions_from_csv(self) -> List[QuestionRow]:
        all_q_from_csv = self.read_csv_to_objects(Paths.QA1_PATH)
        return [
            q for q in all_q_from_csv
            if q.BT == 1 and q.question_content is not None and q.question_content.strip() != ""
        ]

#######################################################################################################################

if __name__ == "__main__":
    unittest.main()
