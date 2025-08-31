from BackEnd.DataPipeline.DB.DBFactory import DBFactory
from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB
from BackEnd.DataPipeline.FAISS_api.FaissEngine import FaissEngine
from BackEnd.Main.Answer import Answer
from BackEnd.Main.QuestionFromUser import QuestionFromUser
from BackEnd.QA.QuestionRow import QuestionRow


import os
from dotenv import load_dotenv
from typing import Optional

from BackEnd.DataObjects.SourceClasses import Source


# from your_module import DBapiMongoDB, FaissEngine, Question


class QuestionAnswerHandler:
    def __init__(self):
        """Initialize the handler: load environment variables and set up DB + FAISS."""
        self.db_api: Optional[DBapiMongoDB] = None
        self.faiss: Optional[FaissEngine] = None
        self._set_up()

    def _set_up(self):
        """Private method: load env variables and set up DB and FAISS."""
        self.db_api = DBFactory.get_prod_db_mongo()
        self.faiss = FaissEngine(dbapi=self.db_api)

    def get_answer_refs_only(self, question: QuestionFromUser)->Answer :
        # Example ref list
        ref_list = [
            "BT_Bava Batra_0_3b:4-7",
            "BT_Bava Batra_0_7b:6-7",
            "BT_Bava Batra_0_13b:9-14a:4"
        ]

        # Create Answer object
        return Answer(
            question=question.question_content,
            filters=question.filters,
            refs=ref_list
        )

    def get_full_answer(self, question: QuestionFromUser)->Answer:
        ans = self.get_answer_refs_only(question)

        for ref in ans.refs:
            collection_name = Source.get_collection_name_from_key(ref)
            src = self.db_api.find_one_source(collection_name, ref)
            ans.srcs.append(src)

        return ans