import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from streamlit.testing.v1 import AppTest

from backend.app.logic.lineage_logic import lineage_path, load_lineage_graph
from backend.models_db.Enums import RelType
from backend.models_db.Rel import Rel
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend.models_dto.EntitySelectOption import EntitySelectOption
from pages.descendants import _copy_text, _lineage_html, _path_sources


def option(key, name, heb=""):
    return EntitySelectOption(key=key, display_en_name=name, display_heb_name=heb)


def rel(child, parent, rel_type=RelType.childOfFather, key=""):
    return Rel(key=key, term1=child, term2=parent, rel_type=rel_type)


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.options = [
            option("a", "Abraham", "אברהם"), option("b", "Isaac", "יצחק"),
            option("c", "Jacob", "יעקב"), option("d", "Dan", "דן"),
            option("e", "Other"), option("x", "Unrelated"),
        ]
        self.rels = [
            rel("b", "a", key="r1"), rel("c", "b", RelType.childOfMother, key="r2"),
            rel("d", "c", key="r3"), rel("d", "e"), rel("b", "a", key="r1b"),
            rel("a", "c"),  # cycle
            rel("x", "a", RelType.descendantOf),
            rel("x", "b", RelType.spouseOf),
            rel("missing", "a"), rel("e", "e"),
        ]
        self.db = MagicMock()
        self.db.getPersonSelectOptions.return_value = self.options
        self.db.get_rels_by_type_for_entities.return_value = self.rels
        self.sources = [
            SourceMetadata("TN_Genesis_0_2:1", rel_keys={"r1", "r1b", "r2"}),
            SourceMetadata("TN_Genesis_0_12:1", rel_keys={"r1b"}),
        ]
        self.db.get_source_metadata_filtered.return_value = self.sources
        self.db.find_one_source_content.side_effect = lambda key: SourceContent(key, ["en", "he"])

    def test_graph_filters_relationships_and_finds_shortest_paths(self):
        graph = load_lineage_graph(self.db)
        call = self.db.get_rels_by_type_for_entities.call_args
        self.assertEqual(call.args[1], ["childOfFather", "childOfMother"])
        self.assertTrue(call.kwargs["as_term1"])
        self.assertFalse(call.kwargs["as_term2"])
        self.assertEqual({o.key for o in graph.start_options(True)}, {"a", "b", "c", "e"})
        self.assertEqual({o.key for o in graph.start_options(False)}, {"a", "b", "c", "d"})
        down = graph.paths_from("a", True)
        self.assertEqual(lineage_path(down, "d"), ["a", "b", "c", "d"])
        self.assertNotIn("x", down)
        self.assertNotIn("e", down)
        up = graph.paths_from("d", False)
        self.assertEqual(lineage_path(up, "a"), ["d", "c", "b", "a"])
        self.assertEqual(lineage_path(up, "e"), ["d", "e"])

    def test_no_generation_limit_and_shortest_route(self):
        options = [option(str(i), str(i)) for i in range(25)]
        self.db.getPersonSelectOptions.return_value = options
        self.db.get_rels_by_type_for_entities.return_value = (
            [rel(str(i + 1), str(i)) for i in range(24)] + [rel("20", "0")]
        )
        graph = load_lineage_graph(self.db)
        self.assertEqual(lineage_path(graph.paths_from("0", True), "24"),
                         ["0", "20", "21", "22", "23", "24"])
        self.assertEqual(len(lineage_path(graph.paths_from("0", True), "19")), 20)

    def test_equal_length_paths_are_deterministic(self):
        self.db.get_rels_by_type_for_entities.return_value = [
            rel("c", "a"), rel("b", "a"), rel("d", "c"), rel("d", "b"),
        ]
        graph = load_lineage_graph(self.db)
        self.assertEqual(lineage_path(graph.paths_from("a", True), "d"), ["a", "b", "d"])

    def test_sources_follow_each_step_in_both_directions(self):
        graph = load_lineage_graph(self.db)
        down = _path_sources(self.db, graph, ["a", "b", "c", "d"], True)
        self.assertEqual([[s.key for s in step] for step in down], [
            ["TN_Genesis_0_2:1", "TN_Genesis_0_12:1"],
            ["TN_Genesis_0_2:1"], [],
        ])
        self.assertEqual(self.db.get_source_metadata_filtered.call_args.kwargs["rel_ids"],
                         ["r1", "r1b", "r2", "r3"])
        up = _path_sources(self.db, graph, ["d", "c", "b", "a"], False)
        self.assertEqual(up, list(reversed(down)))
        text = _copy_text(["Abraham", "Isaac", "Jacob", "Dan"], down, "en")
        self.assertEqual(text, "Abraham (Bereishit (Torah) 2:1, Bereishit (Torah) 12:1) →\n"
                         "Isaac (Bereishit (Torah) 2:1) →\nJacob (No sources recorded.) →\nDan")

    def test_popup_html_deduplicates_and_escapes(self):
        graph = load_lineage_graph(self.db)
        steps = _path_sources(self.db, graph, ["a", "b", "c", "d"], True)
        key = self.sources[0].key
        rendered = _lineage_html(["<Abraham>", "Isaac", "Jacob", "Dan"], steps,
                                 {key: SourceContent(key, ["en", "he"])}, "he")
        self.assertIn("dir='rtl'", rendered)
        self.assertIn("&lt;Abraham&gt;", rendered)
        self.assertEqual(rendered.count('id="sp-lineage-source-0"'), 1)
        self.assertEqual(rendered.count("spOpen('lineage-source-0', event)"), 2)
        self.assertIn("לא נרשמו מקורות", rendered)
        self.assertIn("בראשית", rendered)

    def test_page_is_registered_under_trees(self):
        from frontend import app
        from system_common.Constants import PAGE_DESCENDANTS
        from system_common.UrlPaths import URL_PATHS

        self.assertIn(PAGE_DESCENDANTS, app.TREE_PAGES)
        self.assertEqual(URL_PATHS[PAGE_DESCENDANTS], "trees_descendants")
        self.assertEqual(app._page_title(PAGE_DESCENDANTS, "he"), "צאצאים")
        with patch("pages.trees.render") as render:
            app._renderer(PAGE_DESCENDANTS)("en")
            render.assert_called_once_with("en", selected=PAGE_DESCENDANTS)

    def test_page_modes_localization_and_metrics(self):
        app = AppTest.from_string("""
import streamlit as st
from pages.descendants import render
lang = st.radio("Language", ["en", "he"])
render(lang)
""")
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox[0].options, ["Abraham (אברהם)", "Isaac (יצחק)",
                                                        "Jacob (יעקב)", "Other"])
            app.selectbox[0].select("a").run()
            self.assertEqual(app.selectbox[1].options, ["Isaac (יצחק)", "Jacob (יעקב)", "Dan (דן)"])
            app.selectbox[1].select("d").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.code[0].value,
                             "Abraham (Bereishit (Torah) 2:1, Bereishit (Torah) 12:1) →\n"
                             "Isaac (Bereishit (Torah) 2:1) →\nJacob (No sources recorded.) →\nDan")
            events = app.session_state["_metrics_events"]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["tree_type"], "descendants")
            self.assertEqual(events[0]["entity_id"], "a")
            self.assertEqual(events[0]["entity_ids"], "a,d")
            app.radio[0].set_value("he").run()
            self.assertIn("אברהם (2:1 בראשית", app.code[0].value)
            self.assertIn("יעקב (לא נרשמו מקורות.)", app.code[0].value)
            self.assertEqual(len(app.session_state["_metrics_events"]), 1)
            app.radio[1].set_value("ancestors").run()
            app.selectbox[0].select("d").run()
            self.assertNotIn("אחר", app.selectbox[1].options)
            app.selectbox[1].select("a").run()
            self.assertFalse(app.exception)
            self.assertTrue(app.code[0].value.startswith("דן (לא נרשמו מקורות.) →\nיעקב (2:1 בראשית"))
            self.assertTrue(app.code[0].value.endswith("אברהם"))
            self.assertEqual(app.session_state["_metrics_events"][-1]["tree_type"], "ancestors")
            self.assertEqual(app.session_state["_metrics_events"][-1]["entity_ids"], "d,a")
            self.assertEqual(len(app.session_state["_metrics_events"]), 2)

            app.selectbox[0].select("b").run()
            self.assertIsNone(app.selectbox[1].value)
            self.assertEqual(len(app.code), 0)
            self.assertEqual(len(app.session_state["_metrics_events"]), 2)

    def test_missing_source_content_warns_after_language_change(self):
        app = AppTest.from_string("""
import streamlit as st
from pages.descendants import render
lang = st.radio("Language", ["en", "he"])
render(lang)
""")
        self.db.find_one_source_content.return_value = None
        self.db.find_one_source_content.side_effect = None
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            app.selectbox[0].select("a").run()
            app.selectbox[1].select("b").run()
            self.assertTrue(any("Source content is unavailable" in item.value for item in app.warning))
            app.radio[0].set_value("he").run()
            self.assertTrue(any("תוכן המקור אינו זמין" in item.value for item in app.warning))
            self.assertFalse(app.exception)

    def test_admin_search_is_not_recorded(self):
        app = AppTest.from_string("""
from pages.descendants import render
render("en")
""")
        app.query_params["admin"] = "true"
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            app.selectbox[0].select("a").run()
            app.selectbox[1].select("d").run()
        self.assertFalse(app.exception)
        self.assertNotIn("_metrics_events", app.session_state)


if __name__ == "__main__":
    unittest.main()
