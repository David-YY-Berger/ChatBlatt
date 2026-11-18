import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from streamlit.testing.v1 import AppTest

from backend.app.logic.lineage_logic import lineage_path, load_lineage_graph
from backend.models_db.Enums import RelType, RoleType, TimePeriod
from backend.models_db.Rel import Rel
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend.models_dto.EntitySelectOption import EntitySelectOption
from backend.models_dto.PersonSelectOption import PersonSelectOption
from pages.descendants import _copy_text, _lineage_html, _path_sources, _person_links


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
        rendered = _lineage_html(["<Abraham>", "Isaac", "Jacob", "Dan"],
                                 [("entity", "sources")] * 4, steps,
                                 {key: SourceContent(key, ["en", "he"])}, "he")
        self.assertIn("dir='rtl'", rendered)
        self.assertIn("&lt;Abraham&gt;", rendered)
        self.assertEqual(rendered.count('id="sp-lineage-source-0"'), 1)
        self.assertEqual(rendered.count("spOpen('lineage-source-0', event)"), 2)
        self.assertIn("לא נרשמו מקורות", rendered)
        self.assertIn("בראשית", rendered)
        self.assertIn(self.sources[0].get_sefaria_url(), rendered)

    def test_copy_text_arrows_follow_language_direction(self):
        names = ["אברהם", "יצחק", "יעקב"]
        self.assertEqual(_copy_text(names, [[], []], "he"),
                         "אברהם (לא נרשמו מקורות.) ←\nיצחק (לא נרשמו מקורות.) ←\nיעקב")
        self.assertEqual(_copy_text(names, [[], []], "en"),
                         "אברהם (No sources recorded.) →\nיצחק (No sources recorded.) →\nיעקב")

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
                             "Abraham (אברהם) (Bereishit (Torah) 2:1, Bereishit (Torah) 12:1) →\n"
                             "Isaac (יצחק) (Bereishit (Torah) 2:1) →\n"
                             "Jacob (יעקב) (No sources recorded.) →\nDan (דן)")
            self.assertEqual(app.query_params["lineage_mode"], ["descendants"])
            self.assertEqual(app.query_params["lineage_start"], ["a"])
            self.assertEqual(app.query_params["lineage_target"], ["d"])
            events = app.session_state["_metrics_events"]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["tree_type"], "descendants")
            self.assertEqual(events[0]["entity_id"], "a")
            self.assertEqual(events[0]["entity_ids"], "a,d")
            app.radio[0].set_value("he").run()
            self.assertIn("אברהם (Abraham) (2:1 בראשית", app.code[0].value)
            self.assertIn("יעקב (Jacob) (לא נרשמו מקורות.)", app.code[0].value)
            self.assertEqual(len(app.session_state["_metrics_events"]), 1)
            app.radio[1].set_value("ancestors").run()
            app.selectbox[0].select("d").run()
            self.assertNotIn("אחר", app.selectbox[1].options)
            app.selectbox[1].select("a").run()
            self.assertFalse(app.exception)
            self.assertTrue(app.code[0].value.startswith(
                "דן (Dan) (לא נרשמו מקורות.) ←\nיעקב (Jacob) (2:1 בראשית"))
            self.assertTrue(app.code[0].value.endswith("אברהם (Abraham)"))
            self.assertEqual(app.session_state["_metrics_events"][-1]["tree_type"], "ancestors")
            self.assertEqual(app.session_state["_metrics_events"][-1]["entity_ids"], "d,a")
            self.assertEqual(len(app.session_state["_metrics_events"]), 2)

            app.selectbox[0].select("b").run()
            self.assertIsNone(app.selectbox[1].value)
            self.assertEqual(len(app.code), 0)
            self.assertNotIn("lineage_target", app.query_params)
            self.assertEqual(len(app.session_state["_metrics_events"]), 2)

    def test_shareable_url_restores_selection_and_records_once(self):
        app = AppTest.from_string("""
from pages.descendants import render
render("en")
""")
        app.query_params["lineage_mode"] = "ancestors"
        app.query_params["lineage_start"] = "d"
        app.query_params["lineage_target"] = "a"
        app.query_params["admin"] = "false"
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.radio[0].value, "ancestors")
            self.assertEqual([box.value for box in app.selectbox], ["d", "a"])
            self.assertEqual(app.session_state["_metrics_events"][0]["entity_ids"], "d,a")
            app.run()
            self.assertEqual(len(app.session_state["_metrics_events"]), 1)
            app.query_params["lineage_target"] = "b"
            app.run()
            self.assertEqual(app.selectbox[1].value, "b")
            self.assertEqual(app.session_state["_metrics_events"][-1]["entity_ids"], "d,b")
            self.assertEqual(len(app.session_state["_metrics_events"]), 2)
            self.assertEqual(app.query_params["admin"], ["false"])

    def test_invalid_url_does_not_run_search(self):
        app = AppTest.from_string('from pages.descendants import render\nrender("en")')
        app.query_params["lineage_mode"] = "ancestors"
        app.query_params["lineage_start"] = "d"
        app.query_params["lineage_target"] = "x"
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
        self.assertTrue(app.warning)
        self.assertNotIn("_metrics_events", app.session_state)
        self.assertFalse(app.exception)

    def test_person_source_link_runs_and_records_destination_search(self):
        from components.facets import renderers
        from pages import source_search

        app = AppTest.from_string("""
import streamlit as st
from pages.source_search import render
st.session_state["lang"] = "he"
render("he")
""")
        app.query_params["ent"] = "a"
        app.query_params["via"] = "descendants_source_search"
        with patch.object(source_search, "preload_all_entity_options"), \
             patch.object(source_search, "inject_facet_css"), \
             patch.object(source_search, "render_source_filters"), \
             patch.object(source_search, "_render_search_panel"), \
             patch.object(renderers, "_load_entity_select_options",
                          side_effect=lambda tab: self.options if tab == "people" else []), \
             patch.object(source_search, "run_search",
                          return_value=(SimpleNamespace(total_sources=0), "0s")) as search:
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(search.call_args.args[0].entity_ids, ["a"])
            events = app.session_state["_metrics_events"]
            self.assertEqual([(event["name"], event["app_language"]) for event in events],
                             [("app_search", "he"), ("search_entity_filter", "he")])
            self.assertEqual(events[0]["entity_ids"], "a")
            self.assertEqual(events[1]["entity_id"], "a")

    def test_person_entity_link_records_destination_search_once(self):
        from backend.app.controllers.entity_search import entity_search_controller
        from pages import entity_search

        app = AppTest.from_string("""
from pages.entity_search import _render_entity_search_tab
_render_entity_search_tab("people", "he")
""")
        app.query_params["id"] = "a"
        app.query_params["via"] = "descendants_entity_search"
        handler = SimpleNamespace(
            get_select_options=lambda: self.options,
            get_full_entity=lambda key: self.options[0],
            get_metadata_badges=lambda entity: [],
            get_transient_field_labels=lambda: [],
        )
        with patch.object(entity_search_controller, "get_entity_search_handler", return_value=handler), \
             patch.object(entity_search, "_DEBUG_FE", False), \
             patch.object(entity_search, "_render_filters", side_effect=lambda tab, options, lang: options), \
             patch.object(entity_search, "_render_entity_action_buttons"), \
             patch.object(entity_search, "_render_relationship_fields"):
            app.run()
            app.run()
        self.assertFalse(app.exception)
        events = app.session_state["_metrics_events"]
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]["search_type"], events[0]["entity_ids"],
                          events[0]["app_language"]), ("entity", "a", "he"))

    def test_person_links_labels_and_admin(self):
        person = PersonSelectOption(key="p&1", display_en_name="David", display_heb_name="דוד",
                                    roles=[RoleType.King, RoleType.Prophet], timePeriod=TimePeriod.Tanach)
        with patch("pages.descendants.metrics.shared_params", return_value={"admin": "true"}):
            for lang in ("en", "he"):
                entity_url, sources_url = _person_links(person, lang)
                for url, path, param, via in (
                    (entity_url, "/entity_search_people", "id", "descendants_entity_search"),
                    (sources_url, "/source_search", "ent", "descendants_source_search"),
                ):
                    parsed = urlsplit(url)
                    self.assertEqual(parsed.path, path)
                    self.assertEqual(parse_qs(parsed.query),
                                     {"admin": ["true"], "lang": [lang], param: ["p&1"], "via": [via]})
                from components.entity_option_labels import format_entity_option_label
                label = format_entity_option_label(person, lang)
                rendered = _lineage_html([label], [(entity_url, sources_url)], [], {}, lang)
                self.assertIn("David (דוד) - King, Prophet [Tanach]" if lang == "en"
                              else "דוד (David) - מלך, נביא [תנ״ך]", rendered)
                self.assertEqual(rendered.count("<span class='icon icon-"), 2)
                self.assertEqual(rendered.count("aria-label="), 2)
                self.assertIn("p%261", rendered)
                self.assertIn("admin=true&amp;lang=", rendered)

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
