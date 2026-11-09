import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))


class EntityRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_string("""
import streamlit as st
from types import SimpleNamespace
from backend.models_db.Enums import EntityType
from pages.entity_search import _render_relationship_fields

lang = st.radio("Language", ["en", "he"])
entity_key = st.radio("Entity", ["one", "two"])
entity = SimpleNamespace(
    display_en_name="David", display_heb_name="דוד",
    children=["Solomon", "Nathan"], siblings=["Eliab"], empty=[],
    rel_links={"Solomon": ("solomon", EntityType.EPerson)},
    rel_heb_names={"solomon": "שלמה"}, rel_roles={"solomon": ["King"]},
    rel_keys_by_field={"children": {"Solomon": ["rel1"]}},
)
_render_relationship_fields(entity, [
    ("children", "entity_fields.children"),
    ("siblings", "entity_fields.siblings"),
    ("empty", "entity_fields.spouseOf"),
], lang, entity_key)
""").run()

    def test_collapsed_toggle_switch_and_reset_for_another_entity(self):
        app = self.app
        self.assertEqual([button.label for button in app.button], ["▸ Children (2)", "▸ Siblings (1)"])
        self.assertEqual(len(app.get("popover")), 0)
        app.button(key="relationship_menu_children").click().run()
        self.assertEqual(app.session_state["_entity_relationship_selected"], "children")
        self.assertEqual([popover.proto.popover.label for popover in app.get("popover")],
                         ["• Solomon - king", "• Nathan"])
        links = app.get("link_button")
        query = parse_qs(urlparse(links[0].proto.url).query)
        self.assertEqual(query["rel"], ["rel1"])
        self.assertEqual(query["rel_label"], ["David · Children · Solomon - king"])
        self.assertFalse(links[0].proto.disabled)
        self.assertTrue(links[1].proto.disabled)
        with patch("navigation.go") as go:
            app.button(key="nav_children_" + str(abs(hash("Solomon")))).click().run()
            go.assert_called_once_with("people", id="solomon")
        app.button(key="relationship_menu_siblings").click().run()
        self.assertEqual(app.session_state["_entity_relationship_selected"], "siblings")
        self.assertEqual([popover.proto.popover.label for popover in app.get("popover")], ["• Eliab"])
        app.button(key="relationship_menu_siblings").click().run()
        self.assertEqual(len(app.get("popover")), 0)
        app.button(key="relationship_menu_children").click().run()
        app.radio[1].set_value("two").run()
        self.assertIsNone(app.session_state["_entity_relationship_selected"])
        self.assertEqual(len(app.get("popover")), 0)
        self.assertFalse(app.exception)

    def test_language_switch_preserves_open_section_and_localizes_items(self):
        app = self.app
        app.button(key="relationship_menu_children").click().run()
        app.radio[0].set_value("he").run()
        self.assertEqual(app.button(key="relationship_menu_children").label, "▾ ילדים (2)")
        self.assertEqual(app.get("popover")[0].proto.popover.label, "• שלמה - מלך")
        self.assertEqual(app.session_state["_entity_relationship_selected"], "children")
        self.assertFalse(app.exception)

    def test_no_relationships_shows_message(self):
        app = AppTest.from_string("""
from types import SimpleNamespace
from pages.entity_search import _render_relationship_fields
_render_relationship_fields(SimpleNamespace(children=[]), [("children", "entity_fields.children")], "en", "one")
""").run()
        self.assertEqual(app.info[0].value, "No relationships found for this entity.")
        self.assertEqual(len(app.button), 0)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
