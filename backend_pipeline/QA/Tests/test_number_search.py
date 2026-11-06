import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.controllers.number_search_controller import (
    NumberSearchController,
    UnitSearchRequest,
    UnitSearchResponse,
)
from backend.app.logic.number_search_logic import NumberSearchLogic
from backend.models_db.EntityObjects.ENumber import ENumber
from backend.models_db.EntityObjects.NumberContext import NumberContext
from backend.models_db.Enums import NumberCategory
from system_common.Constants import LANG_HE

frontend_dir = str(Path(__file__).resolve().parents[3] / "frontend")
if frontend_dir not in sys.path:
    sys.path.insert(0, frontend_dir)
with patch("system_common.SystemFunctions.get_secret", return_value="false"):
    from frontend.pages import number_search


class Source:
    def __init__(self, key, order):
        self.key = key
        self.order = order
        self.summary_en = f"English summary {key}"
        self.summary_heb = f"Hebrew summary {key}"

    def __lt__(self, other):
        return self.order < other.order

    def __str__(self):
        return f"English {self.key}"

    def to_heb_str(self):
        return f"Hebrew {self.key}"


class NumberSearchTests(unittest.TestCase):
    def setUp(self):
        self.logic = NumberSearchLogic.__new__(NumberSearchLogic)
        self.logic.db = MagicMock()
        self.first = ENumber(
            key="first", display_en_name="2", en_unit="year",
            numberCategory=NumberCategory.Time,
            contexts=[
                NumberContext(en_context="first context", source_keys=["s1", "s2"]),
                NumberContext(en_context="second context", source_keys=["s1"]),
            ],
        )
        self.second = ENumber(
            key="second", display_en_name="10", en_unit="year",
            numberCategory=None, contexts=[],
        )
        self.other_unit = ENumber(
            key="other", display_en_name="2", en_unit="day",
            numberCategory=NumberCategory.Time,
        )
        self.sources = {
            "first": [Source("s2", 2), Source("s1", 1)],
            "second": [Source("s3", 3)],
            "other": [Source("s4", 4)],
        }
        self.logic.db.get_enumbers_by_unit.return_value = [self.second, self.first]
        self.logic.db.get_enumbers_by_value.return_value = [self.first, self.other_unit]
        self.logic.db.get_source_metadata_by_entity_key.side_effect = self.sources.get

    def test_unit_occurrences_match_number_search_for_selected_unit(self):
        unit_result = self.logic.execute_by_unit("year", LANG_HE)
        number_result = self.logic.execute("2", LANG_HE)
        self.assertEqual([row.value for row in unit_result.rows], ["2", "10"])
        row = unit_result.rows[0]
        self.assertEqual(row.categories, [NumberCategory.Time])
        self.assertEqual(row.mentions, 2)
        occurrences = row.occurrences.by_category[NumberCategory.Time]
        self.assertEqual(occurrences, number_result.by_category[NumberCategory.Time][:3])
        self.assertEqual([occ.source_key for occ in occurrences], ["s1", "s1", "s2"])
        self.assertEqual([occ.en_context for occ in occurrences], [
            "first context", "second context", "first context",
        ])
        self.assertEqual(occurrences[0].source_str, "Hebrew s1")
        self.assertEqual(occurrences[0].summary, "Hebrew summary s1")
        self.assertEqual(unit_result.rows[1].occurrences.by_category[None][0].en_context, None)

    def test_controller_passes_unit_search_language(self):
        controller = NumberSearchController.__new__(NumberSearchController)
        controller._logic = MagicMock()
        response = controller.handle_unit(UnitSearchRequest(unit="year", lang=LANG_HE))
        self.assertTrue(response.success)
        controller._logic.execute_by_unit.assert_called_once_with("year", LANG_HE)

    def test_unit_results_render_source_details_and_popup(self):
        result = self.logic.execute_by_unit("year")
        state = {
            "unit_search_response": UnitSearchResponse(success=True, result=result),
            "unit_search_value": "year",
        }
        content = SimpleNamespace(content=["English passage", "Hebrew passage"])
        source_contents = {"s1": content, "s2": content, "s3": content}
        streamlit = MagicMock()
        streamlit.session_state = state
        streamlit.tabs.side_effect = lambda labels: [MagicMock() for _ in labels]
        with patch.object(number_search, "st", streamlit), \
             patch.object(number_search, "_fetch_source_contents", return_value=source_contents), \
             patch.object(number_search.st_components, "html") as component:
            number_search._render_unit_results("en")

        self.assertEqual(streamlit.expander.call_count, 2)
        rendered = [call.args[0] for call in component.call_args_list]
        first_html = next(text for text in rendered if "first context" in text)
        self.assertIn("second context", first_html)
        self.assertIn("English summary s1", first_html)
        self.assertIn("spOpen('s1', event)", first_html)
        self.assertIn('id="sp-s1"', first_html)
        self.assertIn("English passage", first_html)
        self.assertNotIn("s4", first_html)
        self.assertTrue(any("English s3" in text for text in rendered))

    def test_unit_search_clears_only_its_source_cache(self):
        state = {
            "unit_search_source_contents": {"old": None},
            "number_search_source_contents": {"number": None},
        }
        streamlit = MagicMock()
        streamlit.session_state = state
        with patch.object(number_search, "st", streamlit), \
             patch.object(number_search, "NumberSearchController") as controller:
            number_search._run_unit_search("year", "en")
        self.assertNotIn("unit_search_source_contents", state)
        self.assertIn("number_search_source_contents", state)
        controller.return_value.handle_unit.assert_called_once_with(UnitSearchRequest(unit="year", lang="en"))

    def test_source_fetch_deduplicates_and_does_not_cache_failures(self):
        result = self.logic.execute_by_unit("year")
        streamlit = MagicMock()
        streamlit.session_state = {}
        db = MagicMock()
        def find_content(key):
            if key == "s2":
                raise RuntimeError("database unavailable")
            return f"content {key}"

        db.find_one_source_content.side_effect = find_content
        with patch.object(number_search, "st", streamlit), \
             patch("backend.db.DBFactory.DBFactory.get_prod_db_mongo", return_value=db):
            contents = number_search._fetch_source_contents(
                [row.occurrences for row in result.rows], "unit_cache"
            )
        self.assertEqual(db.find_one_source_content.call_count, 3)
        self.assertEqual(contents["s1"], "content s1")
        self.assertIsNone(contents["s2"])
        self.assertNotIn("unit_cache", streamlit.session_state)
        streamlit.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
