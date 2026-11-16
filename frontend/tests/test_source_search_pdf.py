import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend.app.SourceSearchQuery import SourceSearchQuery
from pages import source_search
from pages.source_search_logic import current_search_url


class SourceSearchPdfTests(unittest.TestCase):
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
