import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from frontend import app


class MobileMenuTests(unittest.TestCase):
    def test_about_dropdown_is_after_home_and_before_number_search(self):
        streamlit = MagicMock()

        def page(*args, **kwargs):
            result = MagicMock()
            result.title = kwargs["title"]
            result.url_path = kwargs["url_path"]
            return result

        streamlit.Page.side_effect = page
        with patch.object(app, "st", streamlit), \
             patch.object(app, "_render_desktop_menu") as desktop, \
             patch.object(app, "_render_mobile_menu") as mobile:
            app._build_navigation("en")

        expected = [
            ("", ["Home"]),
            (
                "About",
                [
                    "About",
                    "What is Eitz Habinah?",
                    "How is Eitz Habinah different from other Torah search tools?",
                    "Pipeline",
                    "About Feyga Menuha",
                    "About the author",
                ],
            ),
            ("", ["Number Search"]),
        ]
        menu_groups = desktop.call_args.args[0]
        self.assertEqual(
            [(title, [page.title for page in pages]) for title, pages in menu_groups[:3]],
            expected,
        )
        self.assertEqual(mobile.call_args.args[0], menu_groups)
        navigation_pages = streamlit.navigation.call_args.args[0]
        self.assertEqual(
            [page.url_path for page in navigation_pages],
            list(app.URL_PATHS.values()),
        )
        streamlit.navigation.assert_called_once_with(
            navigation_pages, position="hidden"
        )

    def test_mcp_page_is_in_desktop_and_mobile_navigation(self):
        streamlit = MagicMock()

        def page(*args, **kwargs):
            result = MagicMock()
            result.title = kwargs["title"]
            result.url_path = kwargs["url_path"]
            return result

        streamlit.Page.side_effect = page
        with patch.object(app, "st", streamlit), \
             patch.object(app, "_render_desktop_menu"), \
             patch.object(app, "_render_mobile_menu") as mobile:
            app._build_navigation("en")

        mobile_groups = mobile.call_args.args[0]
        self.assertIn(
            "mcp_setup",
            [p.url_path for _, pages in mobile_groups for p in pages],
        )
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
             patch.object(app, "_render_desktop_menu"), \
             patch.object(app, "_render_mobile_menu") as mobile:
            app._build_navigation("en")

        mobile_groups = mobile.call_args.args[0]
        tree_group = next(pages for title, pages in mobile_groups if title == "Trees")
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
        expected_titles = [
            "Trees",
            "Family Tree",
            "Places Visited",
            "Descendants",
            "Studied From",
        ]
        self.assertEqual([page.title for page in tree_group], expected_titles)

    def test_selection_changes_popover_key_and_switches_page(self):
        streamlit = MagicMock()
        streamlit.session_state = {}
        home = SimpleNamespace(title="Home", url_path="")
        trees = SimpleNamespace(title="Trees", url_path="trees")
        streamlit.button.side_effect = [False, True]

        with patch.object(app, "st", streamlit):
            menu_groups = [("", [home]), ("Trees", [trees])]
            app._render_mobile_menu(menu_groups, "en")

            calls = streamlit.button.call_args_list
            self.assertEqual([call.args[0] for call in calls], ["Home", "Trees"])
            self.assertEqual([call.kwargs["key"] for call in calls], ["mobile_page_", "mobile_page_trees"])
            self.assertIs(calls[1].kwargs["on_click"], app._close_mobile_menu)
            streamlit.switch_page.assert_called_once_with(trees)
            self.assertEqual(streamlit.popover.call_args.kwargs["key"], "mobile_menu_0")

            calls[1].kwargs["on_click"]()
            streamlit.button.side_effect = [False, False]
            app._render_mobile_menu(menu_groups, "en")
            self.assertEqual(streamlit.popover.call_args.kwargs["key"], "mobile_menu_1")


if __name__ == "__main__":
    unittest.main()
