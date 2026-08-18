# bs"d - lehagdil torah velahadir

from backend.db.DBFactory import DBFactory
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.db.EntityRelManager import EntityRelManager
from backend.faiss_api.FaissEngine import FaissEngine

from backend.models_db.Answer import Answer
from backend.app.SourceSearchQuery import SourceSearchQuery

from typing import Optional, List


class SourceSearchHandler:
    def __init__(self):
        """Initialize the handler: load environment variables and set up db + FAISS."""
        self.db_api: Optional[DBapiMongoDB] = None
        self.faiss: Optional[FaissEngine] = None
        self.entity_rel_manager: Optional[EntityRelManager] = None
        self._set_up()

    def _set_up(self):
        """Private method: load env variables and set up db and FAISS."""
        self.db_api = DBFactory.get_prod_db_mongo()
        self.faiss = FaissEngine(dbapi=self.db_api)
        self.entity_rel_manager = EntityRelManager()

    def get_answer_w_source_metadata(self, query: SourceSearchQuery) -> Answer:

        # Step 1: one DB query for every source that matches the *structural*
        # filters (passage type / entity / relationship selections). This
        # replaces per-item DB round-trips with a single round-trip.
        src_metadata_lst = self.db_api.get_source_metadata_filtered(
            passage_types=query.passage_types,
            entity_ids=query.entity_ids,
            rel_ids=query.rel_ids,
        )

        # Step 2: if free text was given, ask FAISS for the similarity
        # ranking of *keys* and use it purely to re-order the already
        # filtered list above - no per-source DB lookups involved.
        if query.free_text_similarity:
            src_metadata_lst = self.order_by_faiss_similarity(query.free_text_similarity, src_metadata_lst)

        src_metadata_lst = self.populate_entity_rel(src_metadata_lst)
        src_metadata_lst = src_metadata_lst[:query.max_sources]

        return self.create_answer_obj(query, src_metadata_lst)

    def create_answer_obj(self, query:SourceSearchQuery, src_metadata_lst) -> Answer:

        # this code is possibly temporary.. the final front end might expect to be packaged differently..
        entities_from_q = self.db_api.get_entities_by_keys(query.entity_ids) if query.entity_ids else []
        rels_from_q = self.db_api.get_rels_by_keys(query.rel_ids) if query.rel_ids else []
        # Create Answer object
        return Answer(
            free_text_input=query.free_text_similarity,
            src_metadata_lst=src_metadata_lst,
            entities=entities_from_q,
            rels=rels_from_q
        )

    def get_full_answer(self, query: SourceSearchQuery) -> Answer:
        ans = self.get_answer_w_source_metadata(query)

        for src_metadata in ans.src_metadata_lst:
            src = self.db_api.find_one_source_content(src_metadata.key)
            ans.src_contents.append(src)

        return ans

    def order_by_faiss_similarity(
        self, free_text_similarity_text: str, src_metadata_lst: List
    ) -> List:
        """
        Re-rank an already-filtered metadata list by FAISS text-similarity
        order, without any further DB access.

        FAISS ranks the *entire* index in one cheap, vectorized call and
        returns it as a list of keys, ordered nearest-first. We walk that
        ranking and pull matching entries out of ``src_metadata_lst`` (kept
        as a key -> metadata map for O(1) lookup/removal), so the result is
        the intersection of "structurally filtered" and "text-similar",
        ordered by similarity. Anything FAISS didn't rank (e.g. the index is
        stale/incomplete) is appended at the end rather than silently
        dropped, so results never disappear because of a lookup mismatch.
        """
        by_key = {src.key: src for src in src_metadata_lst}
        ranked_keys = self.faiss.search(free_text_similarity_text)

        ordered = [by_key.pop(key) for key in ranked_keys if key in by_key]
        ordered.extend(by_key.values())
        return ordered