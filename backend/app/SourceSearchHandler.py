# bs"d - lehagdil torah velahadir

from backend.db.DBFactory import DBFactory
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.db.EntityRelManager import EntityRelManager
from backend.faiss_api.FaissEngine import FaissEngine, LANG_EN
from backend.bm25_api.BM25Engine import BM25Engine

from backend.models_db.Answer import Answer
from backend.app.SourceSearchQuery import SourceSearchQuery
from backend.common.miscFuncs import detect_query_language
from backend.common.RankFusion import reciprocal_rank_fusion

from typing import Optional, List


class SourceSearchHandler:
    def __init__(self):
        """Initialize the handler: load environment variables and set up db + FAISS + BM25."""
        self.db_api: Optional[DBapiMongoDB] = None
        self.faiss: Optional[FaissEngine] = None
        self.bm25: Optional[BM25Engine] = None
        self.entity_rel_manager: Optional[EntityRelManager] = None
        self._set_up()

    def _set_up(self):
        """Private method: load env variables and set up db, FAISS and BM25."""
        self.db_api = DBFactory.get_prod_db_mongo()
        self.faiss = FaissEngine(dbapi=self.db_api)
        self.bm25 = BM25Engine(dbapi=self.db_api)
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

        # Step 2: if free text was given, ask both FAISS (semantic/embedding
        # similarity) and BM25 (lexical/keyword similarity) for their
        # rankings of *keys*, fuse the two via Reciprocal Rank Fusion, and
        # use that purely to re-order the already-filtered list above - no
        # per-source DB lookups involved, and nothing is filtered out.
        #
        # The query's language (English or Hebrew) determines which
        # language-specific FAISS/BM25 indexes to search; a query mixing both
        # languages is rejected since there's no single index for both.
        if query.free_text_similarity:
            lang = detect_query_language(query.free_text_similarity)
            src_metadata_lst = self.order_by_text_similarity(
                query.free_text_similarity, src_metadata_lst, lang=lang
            )

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

    def populate_entity_rel(self, src_metadata_lst):
        # todo from enetity ids, get the values (name, hebrew name, etc..)
        return src_metadata_lst

    def order_by_text_similarity(
        self, free_text_similarity_text: str, src_metadata_lst: List, lang: str = LANG_EN
    ) -> List:
        """
        Re-rank an already-filtered metadata list by combined text-similarity
        order, without any further DB access or any filtering/limiting of
        `src_metadata_lst` - every item passed in is still present in the
        result, just possibly reordered.

        Two independent similarity signals are combined via Reciprocal Rank
        Fusion (see backend.common.RankFusion):

        - FAISS: semantic/embedding similarity (catches synonyms, paraphrase,
          conceptual matches, translated wording, etc.).
        - BM25:  lexical/keyword similarity (catches exact terms, proper
          names, rare words that embeddings can blur together).

        Each engine ranks its *entire* language-specific index in one cheap,
        vectorized call and returns it as a list of keys, best-first. We fuse
        those two rankings with RRF, then walk the fused ranking and pull
        matching entries out of `src_metadata_lst` (kept as a key -> metadata
        map for O(1) lookup/removal), so the result is the intersection of
        "structurally filtered" and "text-similar", ordered by the fused
        score. Anything neither engine ranked (e.g. an index is stale or
        incomplete) is appended at the end rather than silently dropped, so
        results never disappear because of a lookup mismatch - this method
        only ever reorders, never filters.
        """
        by_key = {src.key: src for src in src_metadata_lst}

        faiss_ranked_keys = self.faiss.search(free_text_similarity_text, lang=lang)
        bm25_ranked_keys = self.bm25.search(free_text_similarity_text, lang=lang)

        fused_keys = reciprocal_rank_fusion([faiss_ranked_keys, bm25_ranked_keys])

        ordered = [by_key.pop(key) for key in fused_keys if key in by_key]
        ordered.extend(by_key.values())
        return ordered