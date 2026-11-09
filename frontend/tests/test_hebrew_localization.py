import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend.app.logic.genealogy_tree_logic import _make_node as genealogy_node
from backend.app.controllers.entity_populator import PersonPopulator
from backend.app.logic.number_search_logic import NumberOccurrenceDTO
from backend.app.logic.studied_from_tree_logic import _make_node as studied_node
from backend.file_utils.HtmlWriter import HtmlWriter
from backend.models_db.Enums import (
    BookCategoryName, NumberCategory, PassageType, PlaceType, RoleType,
    SourceType, SymbolType, TimePeriod,
)
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from components.pdf_export import build_results_pdf
from components.facets import renderers
from components.tree_graph import render_pyvis_graph
from pages.number_search import _occurrences_table, _validate_number
from translations1 import enum_text, get_text


class HebrewLocalizationTests(unittest.TestCase):
    def test_all_filter_enum_values_have_hebrew_labels(self):
        for enum in (BookCategoryName, NumberCategory, PassageType, PlaceType,
                     RoleType, SourceType, SymbolType, TimePeriod):
            for member in enum:
                with self.subTest(member=member):
                    self.assertRegex(enum_text(member, "he"), r"[\u0590-\u05ff]")
                    self.assertEqual(enum_text(member, "en"), member.value)

    def test_source_category_and_html(self):
        meta = SourceMetadata(key="TN_Genesis_0_1:1", passage_types=[PassageType.LAW])
        self.assertIn("תורה", meta.to_heb_str())
        self.assertIn("Torah", str(meta))
        labels = {
            "copy": "העתקה", "no_content": "אין תוכן",
            "passage_types": {"LAW": "הלכה"},
        }
        ans = SimpleNamespace(src_metadata_lst=[meta], src_contents=[])
        result = HtmlWriter().get_full_html(ans, False, "he", labels)
        self.assertIn('dir="rtl"', result)
        self.assertIn(meta.to_heb_str(), result)
        self.assertIn("הלכה", result)
        self.assertIn("אין תוכן", result)
        self.assertIn('title="העתקה"', result)

    def test_number_contexts_and_labels_switch_without_another_search(self):
        occ = NumberOccurrenceDTO(
            en_unit="year", en_context="years of life", source_str="Genesis",
            summary="English", source_key="source", source_str_en="Genesis",
            source_str_heb="בראשית", heb_unit="שנה", heb_context="שנות חיים",
            summary_en="English", summary_heb="תקציר",
        )
        he, _ = _occurrences_table([occ], "#123456", {}, "he")
        en, _ = _occurrences_table([occ], "#123456", {}, "en")
        for text in ("שנה", "שנות חיים", "בראשית", "תקציר", "הקשר", "תקציר המקור", "מקור"):
            self.assertIn(text, he)
        for text in ("year", "years of life", "Genesis", "English", "Context", "Source Summary"):
            self.assertIn(text, en)
        self.assertIn('dir=\'rtl\'', he)
        self.assertIn('dir=\'ltr\'', en)
        self.assertEqual(_validate_number("abc", "he"), get_text("number_search_ui.error_digits", "he"))
        self.assertIsNone(_validate_number("1/3", "he"))

    def test_both_trees_carry_hebrew_names(self):
        entity = SimpleNamespace(key="p", display_en_name="David", display_heb_name="דוד", isWoman=False)
        self.assertEqual(genealogy_node(entity).display_heb_name, "דוד")
        self.assertEqual(studied_node(entity).display_heb_name, "דוד")

    def test_related_entity_hebrew_names_are_retained_by_key(self):
        related = SimpleNamespace(key="p", display_en_name="David", display_heb_name="דוד",
                                  entityType="person", roles=[RoleType.King])
        target = SimpleNamespace(rel_heb_names={}, rel_roles={})
        db = SimpleNamespace(get_entities_by_keys=lambda keys: [related])
        result = PersonPopulator()._resolve_keys_to_names({"p"}, db, target)
        self.assertEqual(result["p"], ("David", "person"))
        self.assertEqual(target.rel_heb_names["p"], "דוד")
        self.assertEqual(target.rel_roles["p"], ["King"])

    def test_graph_uses_hebrew_names_and_mirrors_positions(self):
        node = SimpleNamespace(key="p", display_name="David", display_heb_name="דוד",
                               is_woman=False, is_center=True)
        graph = SimpleNamespace(nodes=[node], edges=[])
        network = unittest.mock.MagicMock()
        with patch("pyvis.network.Network", return_value=network), \
             patch("components.tree_graph.components.html"), \
             patch.object(network, "save_graph"):
            render_pyvis_graph(graph, {"p": (100, 0)}, {"p": "האדם הנבחר"}, lambda edge: {}, "he")
        self.assertEqual(network.add_node.call_args.kwargs["label"], "דוד")
        self.assertEqual(network.add_node.call_args.kwargs["x"], -100)

    def test_facet_selection_survives_language_switch(self):
        option = SimpleNamespace(key="person0001", display_en_name="David",
                                 display_heb_name="דוד", roles=[])
        app = AppTest.from_string("""
import streamlit as st
from components.facets.renderers import _render_entity_select_panel, get_selected_entity_ids
lang = st.radio("Language", ["en", "he"], key="lang")
_render_entity_select_panel({"label": "Person", "key": "person", "entity_tab": "people", "implemented": True}, lang)
st.write(get_selected_entity_ids())
""")
        with patch.object(renderers, "_load_entity_select_options", return_value=[option]):
            app.run()
            app.multiselect[0].set_value(["David (דוד)"]).run()
            app.radio[0].set_value("he").run()
            self.assertEqual(app.session_state["entity_filter_selected_person"], ["David (דוד)"])
            self.assertIn("דוד", app.multiselect[0].options[0])
            self.assertFalse(app.exception)

    def test_pdf_primary_source_title_in_selected_language(self):
        meta = SourceMetadata(key="TN_Genesis_0_1:1")
        ans = SimpleNamespace(src_metadata_lst=[meta], src_contents=[])
        from reportlab.platypus import Paragraph
        texts = []

        def capture(text, *args, **kwargs):
            texts.append(text)
            return Paragraph(text, *args, **kwargs)

        with patch("components.pdf_export.Paragraph", side_effect=capture):
            pdf = build_results_pdf(ans, lang="he")
        self.assertTrue(pdf.startswith(b"%PDF"))
        from bidi.algorithm import get_display
        self.assertIn(get_display(f"1. {meta.to_heb_str()}", base_dir="R"), texts)
        self.assertIn(str(meta), texts)


if __name__ == "__main__":
    unittest.main()
