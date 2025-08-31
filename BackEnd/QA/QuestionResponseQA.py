import csv
import os
import unittest
from typing import List

from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.FileUtils.HtmlWriter import HtmlWriter
from BackEnd.General import Paths
from BackEnd.FileUtils import OsFunctions, LocalPrinter
from BackEnd.General.Enums import FileType
from BackEnd.Main.QuestionFromUser import QuestionFromUser

from BackEnd.QA.QuestionRow import QuestionRow
from BackEnd.Main.QuestionAnswerHandler import QuestionAnswerHandler
from BackEnd.DataObjects.SourceType import SourceType


class TestExample(unittest.TestCase):

    def setUp(self):
        """Runs before every test to set up necessary directories."""
        OsFunctions.clear_create_directory(Paths.QUESTIONS_OUTPUT_DIR)
        self.qaHandler = QuestionAnswerHandler()
        self.htmlWriter = HtmlWriter()
        # self.logger = Logger.Logger()


    def test_foo(self):
        # reserved for any small test
        pass


############################################# 1. Basic Tests ####################################################
    def test_run_all_tests(self):
        question_rows = get_BT_live_questions_from_csv()
        for q in question_rows:
            real_q = q.to_question_from_user(SourceType.BT.name)
            ans = self.qaHandler.get_full_answer(real_q)
            html_ans = self.htmlWriter.get_full_html(ans)
            path = os.path.join(Paths.QUESTIONS_OUTPUT_DIR, q.Question_name)
            LocalPrinter.print_to_file(html_ans, FileType.HTML, path)


############################################# Helper Functions ####################################################

def read_csv_to_objects(file_path: str) -> List[QuestionRow]:
    rows: List[QuestionRow] = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            clean_row = {}
            for k, v in row.items():
                key = k.replace(" ", "_")  # match dataclass field names
                if v.strip() == "":
                    clean_row[key] = None
                elif key in {"BT", "JT", "RM", "TN", "MS"}:
                    clean_row[key] = int(v)  # convert numeric fields
                else:
                    clean_row[key] = v
            rows.append(QuestionRow(**clean_row))
    return rows

def get_BT_live_questions_from_csv() -> List[QuestionRow]:
    all_q_from_CSV = read_csv_to_objects(Paths.QA1_PATH)
    return [
        q for q in all_q_from_CSV
        if q.BT == 1 and q.Question_content is not None and q.Question_content.strip() != ""
    ]
#######################################################################################################################

if __name__ == "__main__":
    unittest.main()
