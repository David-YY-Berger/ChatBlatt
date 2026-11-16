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
from backend.models_dto.EntitySelectOption import EntitySelectOption


def option(key, name, heb=""):
    return EntitySelectOption(key=key, display_en_name=name, display_heb_name=heb)


def rel(child, parent, rel_type=RelType.childOfFather):
    return Rel(term1=child, term2=parent, rel_type=rel_type)


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.options = [
            option("a", "Abraham", "אברהם"), option("b", "Isaac", "יצחק"),
            option("c", "Jacob", "יעקב"), option("d", "Dan", "דן"),
            option("e", "Other"), option("x", "Unrelated"),
        ]
        self.rels = [
            rel("b", "a"), rel("c", "b", RelType.childOfMother),
            rel("d", "c"), rel("d", "e"), rel("b", "a"),
            rel("a", "c"),  # cycle
            rel("x", "a", RelType.descendantOf),
            rel("x", "b", RelType.spouseOf),
            rel("missing", "a"), rel("e", "e"),
        ]
        self.db = MagicMock()
        self.db.getPersonSelectOptions.return_value = self.options
        self.db.get_rels_by_type_for_entities.return_value = self.rels

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
            self.assertEqual(app.code[0].value, "Abraham →\nIsaac →\nJacob →\nDan")
            events = app.session_state["_metrics_events"]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["tree_type"], "descendants")
            self.assertEqual(events[0]["entity_id"], "a")
            self.assertEqual(events[0]["entity_ids"], "a,d")
            app.radio[0].set_value("he").run()
            self.assertEqual(app.code[0].value, "אברהם →\nיצחק →\nיעקב →\nדן")
            self.assertEqual(len(app.session_state["_metrics_events"]), 1)
            app.radio[1].set_value("ancestors").run()
            app.selectbox[0].select("d").run()
            self.assertNotIn("אחר", app.selectbox[1].options)
            app.selectbox[1].select("a").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.code[0].value, "דן →\nיעקב →\nיצחק →\nאברהם")
            self.assertEqual(app.session_state["_metrics_events"][-1]["tree_type"], "ancestors")
            self.assertEqual(app.session_state["_metrics_events"][-1]["entity_ids"], "d,a")
            self.assertEqual(len(app.session_state["_metrics_events"]), 2)

            app.selectbox[0].select("b").run()
            self.assertIsNone(app.selectbox[1].value)
            self.assertEqual(len(app.code), 0)
            self.assertEqual(len(app.session_state["_metrics_events"]), 2)

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
