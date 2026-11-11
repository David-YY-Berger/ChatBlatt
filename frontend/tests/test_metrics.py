import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from streamlit.testing.v1 import AppTest

import metrics
import navigation
from pages import source_search_logic
from pages import source_search
from backend.app.SourceSearchQuery import SourceSearchQuery


class MetricsTests(unittest.TestCase):
    def test_admin_setting_is_preserved_and_invalid_value_fails_closed(self):
        app = AppTest.from_string("""
import streamlit as st
import metrics
metrics.init_admin()
st.write(metrics.admin_params())
if st.button("clear"):
    st.query_params.clear()
    st.rerun()
if st.button("record"):
    metrics.record("app_search", "he", search_type="source")
""")
        app.query_params["admin"] = "TRUE"
        app.run()
        self.assertEqual(app.session_state["_metrics_admin"], "true")
        app.button[0].click().run()
        self.assertEqual(app.query_params["admin"], ["true"])
        app.button[1].click().run()
        self.assertNotIn("_metrics_events", app.session_state)
        app.query_params["admin"] = "invalid"
        app.run()
        self.assertEqual(app.session_state["_metrics_admin"], "true")
        app.query_params["admin"] = "false"
        app.run()
        app.button[1].click().run()
        self.assertEqual(app.session_state["_metrics_events"][0]["app_language"], "he")
        self.assertFalse(app.exception)

    def test_navigation_and_source_search_preserve_admin(self):
        state = {"_metrics_admin": "true"}
        with patch.object(metrics.st, "session_state", state), \
             patch.object(navigation.st, "switch_page") as switch:
            navigation.register_pages({"home": "page"})
            navigation.go("home", id="123")
            switch.assert_called_once_with("page", query_params={"admin": "true", "id": "123"})
        with patch.object(metrics.st, "session_state", state), \
             patch.object(source_search_logic, "flat_url_params", return_value={"q": "abc"}), \
             patch.object(source_search_logic.st, "query_params") as params:
            source_search_logic.sync_url_with_search()
            params.from_dict.assert_called_once_with({"q": "abc", "admin": "true"})
            self.assertEqual(state[source_search_logic.URL_SIG_KEY], (("q", "abc"),))

    def test_source_search_records_structured_fields_without_free_text(self):
        state = {"lang": "he"}
        query = SourceSearchQuery(free_text_similarity="private@example.com", max_sources=50,
                                  rel_ids=["untrusted relationship label"])
        with patch.object(source_search.st, "session_state", state), \
             patch.object(source_search, "collect_search_query", return_value=query), \
             patch.object(source_search, "run_search", return_value=(object(), "1s")), \
             patch.object(source_search, "get_selected_entity_names", return_value=["David"]), \
             patch.object(source_search, "get_selected_entity_metrics",
                          return_value=[("person", "person1", "David")]), \
             patch.object(source_search, "current_search_url", return_value="url"), \
             patch.object(source_search, "current_url_params",
                          return_value={"pt": ["Narrative"], "st": ["Tanach"]}), \
             patch.object(source_search, "sync_url_with_search"), \
             patch.object(source_search.metrics, "record") as record:
            source_search._execute_search()
        search, entity = record.call_args_list
        self.assertEqual(search.args, ("app_search", "he"))
        self.assertEqual(search.kwargs["text_similarity_used"], 1)
        self.assertEqual(search.kwargs["entity_names"], "David")
        self.assertEqual(search.kwargs["relationship_filter_used"], 1)
        self.assertEqual(entity.kwargs["entity_id"], "person1")
        self.assertEqual(entity.kwargs["entity_name"], "David")
        self.assertEqual(search.kwargs["search_id"], entity.kwargs["search_id"])
        self.assertNotIn("private@example.com", str(record.call_args_list))
        self.assertNotIn("untrusted relationship label", str(record.call_args_list))

    def test_failed_search_is_recorded_and_metrics_failure_does_not_break_search(self):
        state = {}
        query = SourceSearchQuery(free_text_similarity="", max_sources=50)
        with patch.object(source_search.st, "session_state", state), \
             patch.object(source_search, "collect_search_query", return_value=query), \
             patch.object(source_search, "_record_search") as record, \
             patch.object(source_search, "run_search", side_effect=ValueError("search failed")):
            source_search._execute_search()
            record.assert_called_once_with(query)
            self.assertEqual(state["_search_error"], "search failed")
        with patch.object(source_search.st, "session_state", state), \
             patch.object(source_search, "collect_search_query", return_value=query), \
             patch.object(source_search, "_record_search", side_effect=ValueError("metrics failed")), \
             patch.object(source_search, "run_search", return_value=(object(), "1s")), \
             patch.object(source_search, "get_selected_entity_names", return_value=[]), \
             patch.object(source_search, "current_search_url", return_value="url"), \
             patch.object(source_search, "sync_url_with_search"), \
             self.assertLogs(source_search.logger, level="ERROR"):
            source_search._execute_search()
            self.assertIn("_search_ans", state)
            self.assertNotIn("_search_error", state)


if __name__ == "__main__":
    unittest.main()
