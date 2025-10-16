from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass
from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.DataPipeline.DB.Collection import CollectionName
from BackEnd.DataPipeline.DB.DBFactory import DBFactory
from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB
from BackEnd.DataPipeline.EntityRelManager import EntityRelManager
from BackEnd.DataPipeline.FAISS_api.FaissEngine import FaissEngine
from BackEnd.DataObjects.Answer import Answer
from BackEnd.Main.QuestionFromUser import QuestionFromUser

from typing import Optional, List

from BackEnd.DataObjects.SourceClasses import SourceContent


# from your_module import DBapiMongoDB, FaissEngine, Question


class SearchHandler:
    def __init__(self):
        """Initialize the handler: load environment variables and set up DB + FAISS."""
        self.db_api: Optional[DBapiMongoDB] = None
        self.faiss: Optional[FaissEngine] = None
        self.entity_rel_manager: Optional[EntityRelManager] = None
        self._set_up()

    def _set_up(self):
        """Private method: load env variables and set up DB and FAISS."""
        self.db_api = DBFactory.get_prod_db_mongo()
        self.faiss = FaissEngine(dbapi=self.db_api)
        self.entity_rel_manager = EntityRelManager(self.db_api)

    def get_answer_w_source_metadata(self, question: QuestionFromUser) -> Answer:

        ref_list = self.ordered_ref_from_faiss(question.question_content)

        src_metadata_lst = self.get_src_metadata(ref_list)

        return self.create_answer(question, src_metadata_lst)

    def create_answer(self, question, src_metadata_lst) -> Answer:
        entities_from_q = [
            e for ent_id in getattr(question, "entities", [])
            if (e := self.entity_rel_manager.get_entity_from_id(ent_id)) is not None
        ]
        rels_from_q = [
            n for ner_id in getattr(question, "rels", [])
            if (n := self.entity_rel_manager.get_rel_from_id(ner_id)) is not None
        ]
        # Create Answer object
        return Answer(
            question_content=question.question_content,
            src_metadata_lst=src_metadata_lst,
            entities=entities_from_q,
            rels=rels_from_q
        )

    def get_full_answer(self, question: QuestionFromUser) -> Answer:
        ans = self.get_answer_w_source_metadata(question)

        for src_metadata in ans.src_metadata_lst:
            # This still returns a string like "BT", "TN", "FS", etc.
            collection_str = SourceClass.get_collection_name_from_key(src_metadata.key)

            # Convert the string to the corresponding Collection object
            try:
                collection_obj = next(
                    c for c in CollectionName.all() if c.name == collection_str
                )
            except StopIteration:
                raise ValueError(f"Unknown collection name '{collection_str}' for key '{src_metadata.key}'")

            # Fetch the Source object using the Collection object
            src = self.db_api.find_one_source_content(collection_obj, src_metadata.key)
            ans.src_contents.append(src)

        return ans


    def ordered_ref_from_faiss(self, prompt: str) -> List[str]:
        # Example ref list
        ref_list = [
            "BT_Bava Batra_0_3b:4-7",
            "BT_Bava Batra_0_7b:6-7",
            "BT_Bava Batra_0_13b:9-14a:4"
        ]
        return ref_list

    def get_src_metadata(self, ref_list):
        src_metadata_lst = []
        for ref in ref_list:

            src_type = SourceClass.get_src_type_from_key(ref)

            src_meta = SourceMetadata(ref, SourceClass.get_book_from_key(ref), src_type,
                                      [], [], ["no summary yet", "עוד לא הוספנו סיכום"])
            src_meta = self.get_src_info_from_db(src_meta)
            src_metadata_lst.append(src_meta)

        return src_metadata_lst

    def get_src_info_from_db(self, src_meta):
        return src_meta