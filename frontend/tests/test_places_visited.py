import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend.app.logic.places_visited_logic import build_rows, load_options_and_relationships
from backend.models_db.Enums import RelType
from backend.models_db.Rel import Rel
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from frontend.pages.places_visited import _results_html
from streamlit.testing.v1 import AppTest


def option(key, name, heb=""):
    return SimpleNamespace(key=key, display_en_name=name, display_heb_name=heb)


def source(key, rels, en="English summary", heb="תקציר"):
    return SourceMetadata(key=key, rel_keys=set(rels), summary_en=en, summary_heb=heb)


class PlacesVisitedTests(unittest.TestCase):
    def setUp(self):
        self.people = [option("p", "David", "דוד"), option("unused", "Unused")]
        self.places = [option("a", "Alpha", "אלף"), option("b", "Beta"), option("c", "Gamma")]
        self.rels = [
            Rel(key="r1", term1="p", term2="a", rel_type=RelType.visited),
            Rel(key="r2", term1="p", term2="b", rel_type=RelType.bornIn),
            Rel(key="r2-duplicate", term1="p", term2="b", rel_type=RelType.bornIn),
            Rel(key="r3", term1="p", term2="c", rel_type=RelType.diedIn),
            Rel(key="bad", term1="a", term2="p", rel_type=RelType.visited),
            Rel(key="other", term1="p", term2="a", rel_type=RelType.prayedAt),
        ]
        self.sources = [
            source("TN_II Chronicles_0_1:1", ["r1"]),
            source("BT_Berakhot_0_2a:1", ["r2"]),
            source("BT_Berakhot_0_3a:1", ["r3"]),
            source("TN_Genesis_0_12:1", ["r2"]),
            source("TN_Genesis_0_2:1", ["r2", "r2-duplicate"]),
        ]
        self.db = MagicMock()
        self.db.getPersonSelectOptions.return_value = self.people
        self.db.getPlaceSelectOptions.return_value = self.places
        self.db.get_rels_by_type_for_entities.return_value = self.rels
        self.db.get_source_metadata_filtered.return_value = self.sources

    def test_selectors_and_rows_for_both_directions(self):
        people, places, rels = load_options_and_relationships(self.db)
        self.assertEqual([o.key for o in people], ["p"])
        self.assertEqual([o.key for o in places], ["a", "b", "c"])
        self.assertEqual([r.key for r in rels], ["r1", "r2", "r2-duplicate", "r3"])
        rows = build_rows(self.db, "p", True, rels, places)
        self.assertEqual([row.other.key for row in rows], ["b", "a", "c"])
        self.assertEqual([s.key for s in rows[0].sources], [
            "TN_Genesis_0_2:1", "TN_Genesis_0_12:1", "BT_Berakhot_0_2a:1",
        ])
        reverse = build_rows(self.db, "a", False, rels, people)
        self.assertEqual([(row.other.key, row.rel_type) for row in reverse], [("p", RelType.visited)])
        self.assertEqual([s.key for s in reverse[0].sources], ["TN_II Chronicles_0_1:1"])

    def test_localized_html_escapes_text_and_opens_source(self):
        people, places, rels = load_options_and_relationships(self.db)
        rows = build_rows(self.db, "p", True, rels, places)
        key = "TN_Genesis_0_2:1"
        contents = {key: SourceContent(key, ["<p>Text</p>", "<p>טקסט</p>"])}
        rendered = _results_html(rows, contents, "he")
        self.assertIn("dir='rtl'", rendered)
        self.assertIn("תקציר", rendered)
        self.assertIn("בראשית", rendered)
        self.assertIn("spOpen('visit-source-0', event)", rendered)
        self.assertIn('id="sp-visit-source-0"', rendered)
        rows[-1].sources = []
        self.assertIn("לא נרשמו מקורות", _results_html(rows, contents, "he"))
        rows[0].other.display_heb_name = "<unsafe>"
        self.assertIn("&lt;unsafe&gt;", _results_html(rows, contents, "he"))

    def test_page_switches_modes_and_submits(self):
        app = AppTest.from_string("""
from pages.places_visited import render
render("en")
""")
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox[0].options), 1)
            app.selectbox[0].select(app.selectbox[0].options[0])
            self.db.find_one_source_content.side_effect = lambda key: SourceContent(key, ["en", "he"])
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.subheader[0].value, "David")
            app.radio[0].set_value("place").run()
            self.assertEqual(len(app.selectbox[0].options), 3)
            app.selectbox[0].select(app.selectbox[0].options[0])
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.subheader[0].value, "Alpha")

    def test_missing_source_warning_survives_rerun(self):
        app = AppTest.from_string("""
import streamlit as st
from pages.places_visited import render
lang = st.radio("Language", ["en", "he"])
render(lang)
""")
        self.db.find_one_source_content.side_effect = RuntimeError("missing content")
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            app.selectbox[0].select(app.selectbox[0].options[0])
            app.button[0].click().run()
            self.assertTrue(any("missing content" in warning.value for warning in app.warning))
            app.radio[0].set_value("he").run()
            self.assertTrue(any("missing content" in warning.value for warning in app.warning))
            self.assertFalse(app.exception)

    def test_search_metrics_for_both_modes_and_reruns(self):
        app = AppTest.from_string("""
import streamlit as st
from pages.places_visited import render
lang = st.radio("Language", ["en", "he"])
render(lang)
""")
        self.db.find_one_source_content.side_effect = lambda key: SourceContent(key, ["en", "he"])
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            app.button[0].click().run()
            self.assertNotIn("_metrics_events", app.session_state)
            app.selectbox[0].select(app.selectbox[0].options[0])
            app.button[0].click().run()
            events = app.session_state["_metrics_events"]
            self.assertEqual(len(events), 1)
            self.assertEqual(
                {key: events[0][key] for key in ("name", "app_language", "search_type",
                                                 "tree_type", "entity_type", "entity_id", "entity_name")},
                {"name": "app_search", "app_language": "en", "search_type": "tree",
                 "tree_type": "places_visited", "entity_type": "person", "entity_id": "p",
                 "entity_name": "David"},
            )
            app.radio[0].set_value("he").run()
            app.radio[1].set_value("place").run()
            self.assertEqual(len(app.session_state["_metrics_events"]), 1)
            app.selectbox[0].select("Alpha (אלף)")
            app.button[0].click().run()
            event = app.session_state["_metrics_events"][1]
            self.assertEqual((event["app_language"], event["tree_type"], event["entity_type"],
                              event["entity_id"], event["entity_name"]),
                             ("he", "places_visited", "place", "a", "Alpha"))
            app.button[0].click().run()
            self.assertEqual(len(app.session_state["_metrics_events"]), 3)
            self.assertFalse(app.exception)

    def test_search_metrics_respects_admin_opt_out(self):
        app = AppTest.from_string("""
import metrics
from pages.places_visited import render
metrics.init_admin()
render("en")
""")
        app.query_params["admin"] = "true"
        self.db.find_one_source_content.side_effect = lambda key: SourceContent(key, ["en", "he"])
        with patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=self.db):
            app.run()
            app.selectbox[0].select(app.selectbox[0].options[0])
            app.button[0].click().run()
            self.assertNotIn("_metrics_events", app.session_state)
            self.assertEqual(app.subheader[0].value, "David")
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
