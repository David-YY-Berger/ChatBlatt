import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend.app.controllers.entity_search import entity_search_controller
from components.facets import renderers
from pages import entity_search


def _options():
    return [
        SimpleNamespace(
            key="person0001", display_en_name="Alice", display_heb_name="",
            isNonJew=False, isWoman=True, isGroup=False, roles=[], timePeriod=None,
        ),
        SimpleNamespace(
            key="person0002", display_en_name="Bob", display_heb_name="",
            isNonJew=False, isWoman=False, isGroup=False, roles=[], timePeriod=None,
        ),
    ]


class SelectorFragmentTests(unittest.TestCase):
    def test_source_selections_are_available_to_search(self):
        app = AppTest.from_string("""
import streamlit as st
from components.facets.renderers import _render_entity_select_panel, get_selected_entity_ids
from pages.source_search_logic import sync_url_with_search
_render_entity_select_panel({"label": "Person", "key": "person", "entity_tab": "people", "implemented": True})
if st.button("Find Sources"):
    st.session_state["searched_ids"] = get_selected_entity_ids()
    sync_url_with_search()
""", default_timeout=30)
        with patch.object(renderers, "_load_entity_select_options", return_value=_options()):
            app.run()
            app.multiselect[0].set_value(["Alice", "Bob"]).run()
            self.assertEqual(app.multiselect[0].value, ["Alice", "Bob"])
            app.button[0].click().run()
            self.assertEqual(app.session_state["entity_filter_selected_person"], ["Alice", "Bob"])
            self.assertEqual(app.session_state["searched_ids"], ["person0001", "person0002"])
            self.assertEqual(app.query_params["ent"], ["person0001,person0002"])
            self.assertFalse(app.exception)

    def test_entity_selection_requires_go_and_filter_clears_selection(self):
        app = AppTest.from_string("""
import streamlit as st
from pages.entity_search import _render_entity_search_tab
_render_entity_search_tab("people", "en")
""")
        handler = SimpleNamespace(get_select_options=_options)
        with patch.object(entity_search_controller, "get_entity_search_handler", return_value=handler), \
             patch.object(entity_search, "_render_entity_detail") as detail:
            app.run()
            self.assertTrue(app.button[0].disabled)
            app.selectbox[0].select("Alice").run()
            self.assertFalse(app.button[0].disabled)
            self.assertEqual(detail.call_count, 0)
            app.button[0].click().run()
            self.assertEqual(app.query_params["id"], ["person0001"])
            self.assertEqual(detail.call_args.args[1], "person0001")
            app.selectbox[0].select("Bob").run()
            self.assertEqual(app.query_params["id"], ["person0001"])
            app.button[0].click().run()
            self.assertEqual(app.query_params["id"], ["person0002"])
            self.assertEqual(detail.call_args.args[1], "person0002")
            app.selectbox[0].select("Alice").run()
            app.session_state["filter_person_gender"] = "men"
            app.run()
            self.assertIsNone(app.selectbox[0].value)
            self.assertTrue(app.button[0].disabled)
            self.assertEqual(app.query_params["id"], ["person0002"])
            self.assertFalse(app.exception)

    def test_tree_selection_requires_go_and_filter_clears_selection(self):
        app = AppTest.from_string("""
import streamlit as st
from components.person_selector import render_person_selector
person = render_person_selector("en", "test_center")
st.write(person or "none")
""")
        handler = SimpleNamespace(get_select_options=_options)
        with patch.object(entity_search_controller, "get_entity_search_handler", return_value=handler):
            app.run()
            app.selectbox[0].select("Alice").run()
            self.assertNotIn("test_center", app.session_state)
            app.button[0].click().run()
            self.assertEqual(app.session_state["test_center"], "person0001")
            app.session_state["person_selector_filter_test_center_gender"] = "men"
            app.run()
            self.assertIsNone(app.selectbox[0].value)
            self.assertTrue(app.button[0].disabled)
            self.assertEqual(app.session_state["test_center"], "person0001")
            self.assertFalse(app.exception)

    def test_duplicate_labels_remain_disambiguated(self):
        options = _options()
        options[1].display_en_name = "Alice"
        self.assertEqual(renderers._unique_option_labels(options), ["Alice (#0001)", "Alice (#0002)"])


if __name__ == "__main__":
    unittest.main()
