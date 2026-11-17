import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from frontend import app


class MobileMenuTests(unittest.TestCase):
    def test_mcp_page_is_in_desktop_and_mobile_navigation(self):
        streamlit = MagicMock()

        def page(*args, **kwargs):
            result = MagicMock()
            result.title = kwargs["title"]
            result.url_path = kwargs["url_path"]
            return result

        streamlit.Page.side_effect = page
        with patch.object(app, "st", streamlit), \
             patch.object(app, "_render_mobile_menu") as mobile:
            app._build_navigation("en")

        desktop_groups = streamlit.navigation.call_args.args[0]
        mobile_groups = mobile.call_args.args[0]
        self.assertIn("mcp_setup", [p.url_path for p in desktop_groups[""]])
        self.assertIn("mcp_setup", [p.url_path for p in mobile_groups[""]])
        self.assertNotEqual(app.URL_PATHS[app.PAGE_MCP], "mcp")

    def test_trees_landing_and_each_tree_are_in_desktop_and_mobile_navigation(self):
        streamlit = MagicMock()

        def page(*args, **kwargs):
            result = MagicMock()
            result.title = kwargs["title"]
            result.url_path = kwargs["url_path"]
            return result

        streamlit.Page.side_effect = page
        with patch.object(app, "st", streamlit), \
             patch.object(app, "_render_mobile_menu") as mobile:
            app._build_navigation("en")

        desktop_groups = streamlit.navigation.call_args.args[0]
        mobile_groups = mobile.call_args.args[0]
        tree_group = desktop_groups["Trees"]
        mobile_tree_group = mobile_groups["Trees"]
        expected_paths = [
            app.URL_PATHS[key] for key in (
                app.PAGE_TREES,
                app.PAGE_FAMILY_TREE,
                app.PAGE_PLACES_VISITED,
                app.PAGE_DESCENDANTS,
                app.PAGE_STUDIED_FROM,
            )
        ]
        self.assertEqual([page.url_path for page in tree_group], expected_paths)
        self.assertEqual([page.url_path for page in mobile_tree_group], expected_paths)
        expected_titles = [
            "Trees",
            "Family Tree",
            "Places Visited",
            "Descendants",
            "Studied From",
        ]
        self.assertEqual([page.title for page in tree_group], expected_titles)
        self.assertEqual([page.title for page in mobile_tree_group], expected_titles)

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
