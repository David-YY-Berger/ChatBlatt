from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass
from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.DataPipeline.DB.Collections import CollectionObjs
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
        self.entity_rel_manager = EntityRelManager()

    def get_answer_w_source_metadata(self, question: QuestionFromUser) -> Answer:

        ref_list = self.ordered_ref_from_faiss(question.question_content, question.max_sources)

        src_metadata_lst = self.create_src_metadata_obj(ref_list)
        src_metadata_lst = self.filter_by_book(src_metadata_lst, question)
        src_metadata_lst = self.populate_entity_rel(src_metadata_lst)
        src_metadata_lst = self.filter_by_entity_rel(question, src_metadata_lst)

        src_metadata_lst = src_metadata_lst[:question.max_sources]

        return self.create_answer_obj(question, src_metadata_lst)

    def create_answer_obj(self, question:QuestionFromUser, src_metadata_lst) -> Answer:

        # this code is possibly temporary.. the final front end might expect to be packaged differently..
        entities_from_q = [
            e for ent_id in question.entities
            if (e := self.entity_rel_manager.get_entity_from_id(ent_id)) is not None
        ]
        rels_from_q = [
            n for rel_id in question.rels
            if (n := self.entity_rel_manager.get_rel_from_id(rel_id)) is not None
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
                    c for c in CollectionObjs.all() if c.name == collection_str
                )
            except StopIteration:
                raise ValueError(f"Unknown collection name '{collection_str}' for key '{src_metadata.key}'")

            # Fetch the Source object using the Collection object
            src = self.db_api.find_one_source_content(collection_obj, src_metadata.key)
            ans.src_contents.append(src)

        return ans


    def ordered_ref_from_faiss(self, prompt: str, max_sources: int) -> List[str]:

        ref_list = self.faiss.search(prompt, max_sources) # can be huge list...
        # Example ref list
        # ref_list = [
        #     "BT_Bava Batra_0_3b:4-7",
        #     "BT_Bava Batra_0_7b:6-7",
        #     "BT_Bava Batra_0_13b:9-14a:4"
        # ]
        return ref_list

    def create_src_metadata_obj(self, ref_list):
        src_metadata_lst = []
        for ref in ref_list:
            src_type = SourceClass.get_src_type_from_key(ref)
            # todo: query db: get summary, entities ids, and rels..
            src_meta = SourceMetadata(
                key = ref,
                source_type=src_type,
                summary_en="no summary yet",
                summary_heb="עוד לא הוספנו סיכום",
                passage_types=[],
                entities=[],
                rels=[]
            )

            src_metadata_lst.append(src_meta)

        return src_metadata_lst


    def filter_by_book(self, src_metadata_lst, question):
        # todo
        return src_metadata_lst


    def populate_entity_rel(self, src_metadata_lst):
        # todo from enetity ids, get the values (name, hebrew name, etc..)
        return src_metadata_lst

    def filter_by_entity_rel(self, question, src_metadata_lst):
        # todo from rel ids, get the values (name, hebrew name, etc..)
        return src_metadata_lst