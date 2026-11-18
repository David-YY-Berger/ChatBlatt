import re
import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from streamlit.testing.v1 import AppTest
from reportlab.pdfbase import pdfmetrics

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend.app.SourceSearchQuery import SourceSearchQuery
from backend.models_db.Enums import PassageType
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from components import pdf_export
from pages import source_search
from pages.source_search_logic import current_search_url


class SourceSearchResultsTests(unittest.TestCase):
    def test_native_results_show_bilingual_details_and_copy_text(self):
        key = "TN_Genesis_0_1:1"
        metadata = SourceMetadata(
            key=key, summary_en="English summary", summary_heb="תקציר",
            passage_types=list(PassageType),
        )
        answer = SimpleNamespace(
            src_metadata_lst=[metadata],
            src_contents=[SourceContent(key, ["<p>First<br>second</p><p>Third</p>", "<p>עברית</p>"])],
        )
        app = AppTest.from_string("""
import streamlit as st
from pages.source_search import _render_results_body
_render_results_body(st.session_state["answer"], "en")
""")
        app.session_state["answer"] = answer
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(
            [expander.label for expander in app.expander],
            ["View source", "Hebrew Content", "English Content"],
        )
        self.assertTrue(all(not expander.proto.expanded for expander in app.expander))
        self.assertTrue(any("English summary" in m.value for m in app.caption))
        self.assertTrue(any("תקציר" in m.value for m in app.caption))
        columns = app.get("column")
        self.assertIn("Bereishit", columns[0].markdown[0].value)
        self.assertIn("בראשית", columns[1].markdown[0].value)
        self.assertEqual(len(columns[1].get("popover")), 1)
        link = app.get("link_button")[0]
        self.assertEqual(link.proto.url, "https://www.sefaria.org/Genesis.1.1")
        self.assertEqual(link.proto.help, "Open in Sefaria")
        self.assertIn("English summary", columns[2].caption[0].value)
        self.assertIn("תקציר", columns[3].caption[0].value)
        badges = next(m.value for m in app.markdown if "Prophecy" in m.value)
        colors = re.findall(r":(\w+)-badge\[", badges)
        self.assertEqual(len(colors), len(PassageType))
        self.assertEqual(len(set(colors)), len(PassageType))
        self.assertIn("First\nsecond\nThird", app.code[0].value)
        self.assertIn("עברית", app.code[0].value)
        self.assertEqual(len(app.get("html")), 2)

    def test_missing_and_partial_content_and_hebrew_labels(self):
        first = SourceMetadata(key="TN_Genesis_0_1:1", summary_en="Fallback")
        second = SourceMetadata(key="TN_Genesis_0_1:2")
        answer = SimpleNamespace(
            src_metadata_lst=[first, second],
            src_contents=[SourceContent(first.key, ["Only English"])],
        )
        app = AppTest.from_string("""
import streamlit as st
from pages.source_search import _render_results_body
_render_results_body(st.session_state["answer"], "he")
""")
        app.session_state["answer"] = answer
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(
            [expander.label for expander in app.expander],
            ["הצגת המקור", "מקור באנגלית", "הצגת המקור"],
        )
        self.assertTrue(all(not expander.proto.expanded for expander in app.expander))
        self.assertTrue(any("Fallback" in m.value for m in app.caption))
        columns = app.get("column")
        self.assertIn("Bereishit", columns[0].markdown[0].value)
        self.assertIn("בראשית", columns[1].markdown[0].value)
        self.assertIn("Fallback", columns[2].caption[0].value)
        self.assertFalse(columns[3].caption)
        self.assertIn("Only English", app.code[0].value)
        self.assertEqual(len(app.get("html")), 1)
        self.assertEqual(app.info[0].value, "תוכן המקור אינו זמין")


class SourceSearchPdfTests(unittest.TestCase):
    def test_download_widget_defers_generation_without_rerun(self):
        app = AppTest.from_string("""
import streamlit as st
from pages.source_search import _render_download_button
_render_download_button(st.session_state["answer"], "en")
""")
        app.session_state["answer"] = SimpleNamespace(src_metadata_lst=[], src_contents=[])
        with patch.object(source_search, "build_results_pdf") as build:
            app.run()
        self.assertFalse(app.exception)
        build.assert_not_called()
        download = app.get("download_button")[0].proto
        self.assertTrue(download.deferred_file_id)
        self.assertTrue(download.ignore_rerun)

    def test_hebrew_cantillation_is_embedded_and_shaped(self):
        pdf_export._register_fonts()
        text = "בְּרֵאשִׁ֖ית בָּרָ֣א"
        paragraph = pdf_export._text_flowables(f"<b>{text}</b> (ABC123)", 11, 400, html=True)[0]
        paragraph.wrap(400, 500)
        hebrew_fragments = [
            frag for line in paragraph.blPara.lines for frag in line.words
            if frag.fontName == pdf_export.HEBREW_FONT_BOLD
        ]
        self.assertTrue(hebrew_fragments)
        self.assertTrue(any(
            any(position.x_offset or position.y_offset for position in frag.text.__shapeData__)
            for frag in hebrew_fragments
        ))
        for font_name in (pdf_export.HEBREW_FONT, pdf_export.HEBREW_FONT_BOLD):
            font = pdfmetrics.getFont(font_name)
            self.assertTrue(all(ord(char) in font.face.charWidths for char in text if char != " "))
            self.assertTrue(all(ord(char) in font.face.charWidths for char in "(ABC123)"))

        meta = SourceMetadata(key="TN_Genesis_0_1:1", summary_heb=text)
        ans = SimpleNamespace(
            src_metadata_lst=[meta],
            src_contents=[SourceContent(meta.key, ["English", f"<b>{text}</b>"])],
        )
        for lang in ("en", "he"):
            pdf = pdf_export.build_results_pdf(ans, lang=lang)
            self.assertTrue(pdf.startswith(b"%PDF-"))
            self.assertIn(b"FreeSerif", pdf)

    def test_shared_all_entity_link_runs_with_toggle_enabled(self):
        app = AppTest.from_string("""
from pages.source_search import render
render("en")
""")
        app.query_params["ent"] = "person,place"
        app.query_params["entity_match"] = "all"
        with patch.object(source_search, "preload_all_entity_options"), \
             patch.object(source_search, "inject_facet_css"), \
             patch.object(source_search, "render_source_filters"), \
             patch.object(source_search, "render_entity_facets"), \
             patch.object(source_search, "_render_search_panel"), \
             patch.object(source_search, "_record_search"), \
             patch.object(source_search, "get_selected_entity_names", return_value=[]), \
             patch.object(source_search, "run_search", return_value=(SimpleNamespace(total_sources=0), "0s")) as search, \
             patch("pages.source_search_logic.set_selected_filters"), \
             patch("pages.source_search_logic.set_selected_entity_option_keys") as set_entities, \
             patch("pages.source_search_logic.get_selected_entity_ids", return_value=["person", "place"]), \
             patch("pages.source_search_logic.get_selected_entity_option_keys", return_value=["person", "place"]):
            app.run()
            self.assertTrue(app.toggle[0].value)
            self.assertTrue(search.call_args.args[0].match_all_entities)
            set_entities.assert_called_once_with(["person", "place"])
            self.assertFalse(app.exception)

    def test_entity_match_toggle_applies_on_search_and_survives_language_change(self):
        app = AppTest.from_string("""
import streamlit as st
from pages.source_search import render
lang = st.radio("Language", ["en", "he"], key="lang")
render(lang)
""")
        ans = SimpleNamespace(total_sources=0)
        with patch.object(source_search, "preload_all_entity_options"), \
             patch.object(source_search, "inject_facet_css"), \
             patch.object(source_search, "render_source_filters"), \
             patch.object(source_search, "render_entity_facets"), \
             patch.object(source_search, "_render_search_panel"), \
             patch.object(source_search, "_record_search"), \
             patch.object(source_search, "get_selected_entity_names", return_value=[]), \
             patch.object(source_search, "run_search", return_value=(ans, "0s")) as search, \
             patch("pages.source_search_logic.get_selected_entity_ids", return_value=["person", "place"]), \
             patch("pages.source_search_logic.get_selected_entity_option_keys", return_value=["person", "place"]):
            app.run()
            self.assertFalse(app.toggle[0].value)
            app.button[0].click().run()
            self.assertFalse(search.call_args.args[0].match_all_entities)
            self.assertNotIn("entity_match", app.query_params)
            app.toggle[0].set_value(True).run()
            self.assertEqual(search.call_count, 1)
            app.radio[0].set_value("he").run()
            self.assertTrue(app.toggle[0].value)
            app.button[0].click().run()
            self.assertTrue(search.call_args.args[0].match_all_entities)
            self.assertEqual(app.query_params["entity_match"], ["all"])
            self.assertFalse(app.exception)

    def test_deferred_download_uses_executed_search_url_without_session_state(self):
        params = {
            "q": "David & Solomon",
            "pt": ["LAW", "NARRATIVE"],
            "st": ["TANACH"],
            "ent": ["person1", "person2"],
            "rel": ["rel1"],
            "rel_label": "Teacher & student",
        }
        with patch("pages.source_search_logic.current_url_params", return_value=params):
            url = current_search_url()
        self.assertEqual(parse_qs(urlsplit(url).query), {
            key: [",".join(value) if isinstance(value, list) else value]
            for key, value in params.items()
        })
        state = {"_search_url": url, "_search_entity_names": ["David"]}
        ans = SimpleNamespace(src_metadata_lst=[], src_contents=[])
        with patch.object(source_search.st, "session_state", state), \
             patch.object(source_search.st, "markdown"), \
             patch.object(source_search.st, "container", return_value=nullcontext()), \
             patch.object(source_search.st, "download_button") as download:
            source_search._render_download_button(ans, "en")
            callback = download.call_args.kwargs["data"]
            self.assertEqual(download.call_args.kwargs["on_click"], "ignore")
        with patch.object(source_search.st, "session_state", {}):
            pdf = callback()
        self.assertTrue(b"/URI (" + url.encode("ascii") + b")" in pdf)

    def test_pagination_keeps_original_search_url_and_entity_names(self):
        query = SourceSearchQuery(free_text_similarity="", max_sources=50, match_all_entities=True)
        state = {
            "_search_url": "https://example.test/source_search?q=original",
            "_search_entity_names": ["Original"],
        }
        with patch.object(source_search.st, "session_state", state), \
             patch.object(source_search, "run_search", return_value=(object(), "1s")) as search, \
             patch.object(source_search, "get_selected_entity_names", return_value=["Changed"]), \
             patch.object(source_search, "current_search_url", return_value="https://example.test/source_search?q=changed"), \
             patch.object(source_search, "sync_url_with_search") as sync:
            source_search._execute_search(query, page=1)
            source_search._execute_search(query, page=0)
        self.assertEqual(state["_search_url"], "https://example.test/source_search?q=original")
        self.assertEqual(state["_search_entity_names"], ["Original"])
        self.assertTrue(all(call.args[0].match_all_entities for call in search.call_args_list))
        sync.assert_not_called()

    def test_new_search_captures_current_url_and_entity_names(self):
        query = SourceSearchQuery(free_text_similarity="new", max_sources=50)
        state = {}
        with patch.object(source_search.st, "session_state", state), \
             patch.object(source_search, "collect_search_query", return_value=query), \
             patch.object(source_search, "run_search", return_value=(object(), "1s")), \
             patch.object(source_search, "get_selected_entity_names", return_value=["New"]), \
             patch.object(source_search, "current_search_url", return_value="https://example.test/source_search?q=new"), \
             patch.object(source_search, "sync_url_with_search") as sync:
            source_search._execute_search()
        self.assertEqual(state["_search_url"], "https://example.test/source_search?q=new")
        self.assertEqual(state["_search_entity_names"], ["New"])
        sync.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
