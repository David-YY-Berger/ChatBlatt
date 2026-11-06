import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.SourceSearchHandler import SourceSearchHandler
from backend.app.SourceSearchQuery import SourceSearchQuery
from backend.bm25_api.BM25Engine import BM25Engine, tokenize
from backend.models_db.Enums import PassageType, SourceType
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend.similarity_search_api.BaseSimilarityEngine import BaseSimilarityEngine
from backend_pipeline.QA.Tests.conftest import FakeDBapi


class SourceSearchTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDBapi.create()
        self.handler = SourceSearchHandler.__new__(SourceSearchHandler)
        self.handler.db_api = self.db
        self.handler.faiss = MagicMock()
        self.handler.bm25 = MagicMock()

    def add_source(self, key, passage_types=(), entities=(), rels=()):
        src = SourceMetadata(key, passage_types=list(passage_types),
                             entity_keys=set(entities), rel_keys=set(rels))
        self.db.insert_source_metadata(src)
        return src

    def test_all_filters_intersect_before_similarity_and_limit(self):
        first = self.add_source("TN_Genesis_0_1:1", [PassageType.LAW], ["e1"], ["r1"])
        second = self.add_source("TN_Genesis_0_1:2", [PassageType.LAW], ["e2"], ["r2"])
        self.add_source("BT_Genesis_0_1a:1", [PassageType.LAW], ["e1"], ["r1"])
        self.add_source("TN_Exodus_0_1:1", [PassageType.LAW], ["e1"], ["r1"])
        self.add_source("TN_Genesis_0_1:3", [PassageType.PROPHECY], ["e1"], ["r1"])
        self.add_source("TN_Genesis_0_1:4", [PassageType.LAW], ["other"], ["r1"])
        self.add_source("TN_Genesis_0_1:5", [PassageType.LAW], ["e1"], ["other"])
        unrelated = [f"unrelated-{i}" for i in range(1000)]
        self.handler.faiss.search.return_value = [second.key] + unrelated + [first.key]
        self.handler.bm25.search.return_value = [first.key, second.key]
        query = SourceSearchQuery(
            "prayer", 1, src_types=[SourceType.TN],
            passage_types=[PassageType.LAW, PassageType.STORY_SAGES],
            book_names=["Genesis", "Joshua"], entity_ids=["e1", "e2"],
            rel_ids=["r1", "r2"],
        )
        self.db.get_entities_by_keys = MagicMock(return_value=[])
        self.db.get_rels_by_keys = MagicMock(return_value=[])
        self.db.find_one_source_content = MagicMock(side_effect=lambda key: key)
        answer = self.handler.get_full_answer(query)
        self.assertEqual([s.key for s in answer.src_metadata_lst], [second.key])
        self.assertEqual(answer.src_contents, [second.key])
        self.assertEqual(answer.total_sources, 2)
        self.handler.faiss.search.assert_called_once_with("prayer", top_k=None, lang="en")
        self.handler.bm25.search.assert_called_once_with("prayer", top_k=None, lang="en")

    def test_pagination_returns_requested_window_and_total_count(self):
        sources = [self.add_source(f"TN_Genesis_0_1:{i}") for i in range(5)]
        self.db.get_entities_by_keys = MagicMock(return_value=[])
        self.db.get_rels_by_keys = MagicMock(return_value=[])
        self.db.find_one_source_content = MagicMock(side_effect=lambda key: key)

        answer = self.handler.get_full_answer(
            SourceSearchQuery("", 2, offset=2)
        )

        self.assertEqual(answer.src_metadata_lst, sources[2:4])
        self.assertEqual(answer.src_contents, [sources[2].key, sources[3].key])
        self.assertEqual(answer.total_sources, 5)
        self.db.find_one_source_content.assert_has_calls([
            unittest.mock.call(sources[2].key),
            unittest.mock.call(sources[3].key),
        ])

    def test_unranked_sources_are_retained_and_hebrew_index_is_used(self):
        a = self.add_source("TN_Genesis_0_1:1", entities=["e"])
        b = self.add_source("TN_Genesis_0_1:2", entities=["e"])
        self.handler.faiss.search.return_value = [b.key]
        self.handler.bm25.search.return_value = []
        self.db.get_entities_by_keys = MagicMock(return_value=[])
        with self.assertLogs("backend.app.SourceSearchHandler", level="WARNING") as logs:
            answer = self.handler.get_answer_w_source_metadata(
                SourceSearchQuery("תפילה", 10, entity_ids=["e"])
            )
        self.assertEqual([s.key for s in answer.src_metadata_lst], [b.key, a.key])
        self.assertIn("could not rank 1 of 2", logs.output[0])
        self.handler.faiss.search.assert_called_once_with("תפילה", top_k=None, lang="heb")

    def test_unrelated_global_ranks_do_not_distort_filtered_fusion(self):
        a = self.add_source("TN_Genesis_0_1:1")
        b = self.add_source("TN_Genesis_0_1:2")
        self.handler.faiss.search.return_value = [b.key] + [
            f"other-{i}" for i in range(1000)
        ] + [a.key]
        self.handler.bm25.search.return_value = [a.key, b.key]
        ranked = self.handler.order_by_text_similarity("prayer", [a, b])
        self.assertEqual([s.key for s in ranked], [b.key, a.key])

    def test_unavailable_rankings_fail_instead_of_silently_ignoring_sort(self):
        a = self.add_source("TN_Genesis_0_1:1")
        self.handler.faiss.search.return_value = []
        self.handler.bm25.search.return_value = []
        with self.assertRaisesRegex(RuntimeError, "could not rank any matching sources"):
            self.handler.order_by_text_similarity("prayer", [a])

    def test_empty_filter_result_does_not_require_similarity_indexes(self):
        answer = self.handler.get_answer_w_source_metadata(
            SourceSearchQuery("prayer", 10, book_names=["Genesis"])
        )
        self.assertEqual(answer.src_metadata_lst, [])
        self.handler.faiss.search.assert_not_called()
        self.handler.bm25.search.assert_not_called()

    def test_no_text_preserves_filtered_order_without_using_indexes(self):
        a = self.add_source("TN_Genesis_0_1:1")
        self.add_source("BT_Berakhot_0_2a:1")
        answer = self.handler.get_answer_w_source_metadata(
            SourceSearchQuery("", 10, src_types=[SourceType.TN])
        )
        self.assertEqual([s.key for s in answer.src_metadata_lst], [a.key])
        self.handler.faiss.search.assert_not_called()
        self.handler.bm25.search.assert_not_called()

    def test_book_names_are_exact_and_regex_escaped(self):
        a = self.add_source("TN_A.B_0_1:1")
        self.add_source("TN_AxB_0_1:1")
        self.add_source("TN_A.B extra_0_1:1")
        found = self.db.get_source_metadata_filtered(book_names=["A.B"])
        self.assertEqual([s.key for s in found], [a.key])

    def test_multiple_source_types_are_ored(self):
        a = self.add_source("TN_Genesis_0_1:1")
        b = self.add_source("BT_Berakhot_0_2a:1")
        self.add_source("MS_Berakhot_0_1:1")
        found = self.db.get_source_metadata_filtered(src_types=[SourceType.TN, SourceType.BT])
        self.assertEqual([s.key for s in found], [a.key, b.key])


class BM25RankingTests(unittest.TestCase):
    def test_unmatched_documents_do_not_get_arbitrary_lexical_rank(self):
        engine = BM25Engine.__new__(BM25Engine)
        engine._bm25_models = {}
        corpus = [tokenize(text) for text in ["prayer prayer", "unrelated", "other"]]
        self.assertEqual(engine._rank_all("en", corpus, "prayer", 3), [0])
        self.assertEqual(engine._rank_all("en", corpus, "missing", 3), [])

    def test_matched_documents_with_negative_scores_are_still_ranked(self):
        engine = BM25Engine.__new__(BM25Engine)
        engine._bm25_models = {}
        corpus = [tokenize(text) for text in ["common", "common", "unrelated"]]
        self.assertEqual(engine._rank_all("en", corpus, "common", 3), [0, 1])

    def test_uncapped_search_ranks_the_entire_index(self):
        engine = MagicMock()
        engine._check_lang.return_value = "en"
        engine._get_index.return_value = "index"
        engine._get_metadata.return_value = ["first", "last"]
        engine._index_size.return_value = 100001
        engine._rank_all.return_value = [1, 0]
        with patch("builtins.print"):
            result = BaseSimilarityEngine.search(engine, "prayer", top_k=None)
        engine._rank_all.assert_called_once_with("en", "index", "prayer", 100001)
        self.assertEqual(result, ["last", "first"])


frontend_dir = str(Path(__file__).resolve().parents[3] / "frontend")
if frontend_dir not in sys.path:
    sys.path.insert(0, frontend_dir)
with patch("system_common.SystemFunctions.get_secret", return_value="false"):
    from frontend.pages import source_search_logic


class SourceSearchFormTests(unittest.TestCase):
    def test_collects_all_form_parameters(self):
        state = SimpleNamespace(session_state={"free_text_query": " prayer "})
        with patch.object(source_search_logic, "st", state), \
             patch.object(source_search_logic, "get_selected_passage_types", return_value=[PassageType.LAW]), \
             patch.object(source_search_logic, "get_selected_book_names", return_value=["Genesis"]), \
             patch.object(source_search_logic, "get_selected_entity_ids", return_value=["e"]), \
             patch.object(source_search_logic, "get_relationship_search", return_value={"rel_ids": ["r"]}):
            query = source_search_logic.collect_search_query()
        self.assertEqual(query.free_text_similarity, "prayer")
        self.assertEqual(query.max_sources, 50)
        self.assertEqual(query.passage_types, [PassageType.LAW])
        self.assertEqual(query.book_names, ["Genesis"])
        self.assertEqual(query.entity_ids, ["e"])
        self.assertEqual(query.rel_ids, ["r"])

    def test_shared_url_restores_all_filters(self):
        params = {
            source_search_logic.PARAM_SOURCE_TEXT: "prayer",
            source_search_logic.PARAM_SOURCE_PASSAGE_TYPES: "LAW",
            source_search_logic.PARAM_SOURCE_BOOKS: "Genesis",
            source_search_logic.PARAM_SOURCE_ENTITIES: "e",
            source_search_logic.PARAM_SOURCE_RELS: "r",
            source_search_logic.PARAM_SOURCE_REL_LABEL: "relationship",
        }
        state = SimpleNamespace(session_state={}, query_params=params)
        with patch.object(source_search_logic, "st", state), \
             patch.object(source_search_logic, "set_selected_filters") as filters, \
             patch.object(source_search_logic, "set_selected_entity_option_keys") as entities:
            self.assertTrue(source_search_logic.apply_url_params())
            self.assertFalse(source_search_logic.apply_url_params())
        self.assertEqual(state.session_state["free_text_query"], "prayer")
        filters.assert_called_once_with(["LAW"], ["Genesis"])
        entities.assert_called_once_with(["e"])
        self.assertEqual(state.session_state[source_search_logic.REL_SEARCH_KEY],
                         {"rel_ids": ["r"], "label": "relationship"})


if __name__ == "__main__":
    unittest.main()
