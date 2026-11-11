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
from backend.models_db.Enums import RoleType, TimePeriod
from backend.models_dto.PersonSelectOption import PersonSelectOption
from components.entity_option_labels import unique_entity_option_labels
from components.facets import renderers


PEOPLE = [
    PersonSelectOption(
        key="person0001", display_en_name="David", display_heb_name="דוד",
        roles=[RoleType.King, RoleType.Prophet], timePeriod=TimePeriod.Tanach,
    ),
    PersonSelectOption(
        key="person0002", display_en_name="David", display_heb_name="דוד",
        roles=[RoleType.King, RoleType.Prophet], timePeriod=TimePeriod.Tanach,
    ),
    PersonSelectOption(key="period", display_en_name="Period", timePeriod=TimePeriod.Amoraim),
    PersonSelectOption(key="role", display_en_name="Role", roles=[RoleType.King]),
    PersonSelectOption(key="unknown", display_en_name="Unknown"),
]


class PersonSelectorLabelTests(unittest.TestCase):
    def test_entity_and_tree_labels_and_selection(self):
        handler = SimpleNamespace(get_select_options=lambda: PEOPLE)
        with patch.object(entity_search_controller, "get_entity_search_handler", return_value=handler):
            for selector in ("entity", "tree"):
                with self.subTest(selector=selector):
                    source = (
                        'from pages.entity_search import _render_entity_selector\n'
                        '_render_entity_selector("people", options, lang)\n'
                        if selector == "entity" else
                        'from components.person_selector import render_person_selector\n'
                        'render_person_selector(lang, "center")\n'
                    )
                    app = AppTest.from_string(
                        'import streamlit as st\n'
                        'from frontend.tests.test_person_selector_labels import PEOPLE as options\n'
                        'lang = st.radio("Language", ["en", "he"])\n' + source,
                        default_timeout=30,
                    ).run()
                    self.assertEqual(app.selectbox[0].options, [
                        "David (דוד) - King, Prophet [Tanach] (#0001)",
                        "David (דוד) - King, Prophet [Tanach] (#0002)",
                        "Period [Amoraim]", "Role - King", "Unknown",
                    ])
                    app.selectbox[0].select("David (דוד) - King, Prophet [Tanach] (#0002)").run()
                    app.radio[0].set_value("he").run()
                    self.assertEqual(app.selectbox[0].options[1], "דוד (David) - מלך, נביא [תנ״ך] (#0002)")
                    self.assertEqual(app.selectbox[0].value, "David (דוד) - King, Prophet [Tanach] (#0002)")
                    app.button[0].click().run()
                    if selector == "entity":
                        self.assertEqual(app.query_params["id"], ["person0002"])
                    else:
                        self.assertEqual(app.session_state["center"], "person0002")
                    self.assertFalse(app.exception)

    def test_source_labels_language_and_selected_keys(self):
        app = AppTest.from_string("""
import streamlit as st
from components.facets.renderers import _render_entity_select_panel, get_selected_entity_ids, get_selected_entity_option_keys
lang = st.radio("Language", ["en", "he"])
_render_entity_select_panel({"label": "Person", "key": "person", "entity_tab": "people", "implemented": True}, lang)
st.session_state["ids"] = get_selected_entity_ids()
st.session_state["option_keys"] = get_selected_entity_option_keys()
""", default_timeout=30)
        with patch.object(renderers, "_load_entity_select_options", return_value=PEOPLE):
            app.run()
            label = "David (דוד) - King, Prophet [Tanach] (#0002)"
            self.assertIn(label, app.multiselect[0].options)
            app.multiselect[0].set_value([label]).run()
            app.radio[0].set_value("he").run()
            self.assertEqual(app.multiselect[0].options[1], "דוד (David) - מלך, נביא [תנ״ך] (#0002)")
            self.assertEqual(app.session_state["ids"], ["person0002"])
            self.assertEqual(app.session_state["option_keys"], ["person0002"])
            self.assertFalse(app.exception)

    def test_duplicate_key_suffixes_use_full_keys(self):
        options = [
            PersonSelectOption(key="first0001", display_en_name="David"),
            PersonSelectOption(key="second0001", display_en_name="David"),
        ]
        self.assertEqual(unique_entity_option_labels(options), [
            "David (#first0001)", "David (#second0001)",
        ])


if __name__ == "__main__":
    unittest.main()
