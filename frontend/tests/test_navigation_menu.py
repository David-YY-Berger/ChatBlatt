import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from frontend import app


class MobileMenuTests(unittest.TestCase):
    def test_selection_changes_popover_key_and_switches_page(self):
        streamlit = MagicMock()
        streamlit.session_state = {}
        home = SimpleNamespace(title="Home", url_path="")
        trees = SimpleNamespace(title="Trees", url_path="trees")
        streamlit.button.side_effect = [False, True]

        with patch.object(app, "st", streamlit):
            app._render_mobile_menu({"": [home], "Trees": [trees]}, "en")

            calls = streamlit.button.call_args_list
            self.assertEqual([call.args[0] for call in calls], ["Home", "Trees"])
            self.assertEqual([call.kwargs["key"] for call in calls], ["mobile_page_", "mobile_page_trees"])
            self.assertIs(calls[1].kwargs["on_click"], app._close_mobile_menu)
            streamlit.switch_page.assert_called_once_with(trees)
            self.assertEqual(streamlit.popover.call_args.kwargs["key"], "mobile_menu_0")

            calls[1].kwargs["on_click"]()
            streamlit.button.side_effect = [False, False]
            app._render_mobile_menu({"": [home], "Trees": [trees]}, "en")
            self.assertEqual(streamlit.popover.call_args.kwargs["key"], "mobile_menu_1")


if __name__ == "__main__":
    unittest.main()
