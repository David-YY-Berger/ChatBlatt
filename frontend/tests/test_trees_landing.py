import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from system_common.Constants import PAGE_PLACES_VISITED, PAGE_TREES
from pages import home


class TreesLandingTests(unittest.TestCase):
    def test_landing_shows_four_illustrated_choices_and_routes_to_selected_tree(self):
        app = AppTest.from_string("""
from pages.trees import render
render("en")
""")
        with patch("pages.trees.navigation.go") as go:
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("imgs")), 4)
            self.assertEqual(
                [button.label for button in app.button],
                ["Family Tree", "Places Visited", "Descendants", "Studied From"],
            )
            app.button[1].click().run()
            go.assert_called_once_with(PAGE_PLACES_VISITED)
            self.assertFalse(app.exception)

    def test_landing_translates_tree_choices_and_descriptions_to_hebrew(self):
        app = AppTest.from_string("""
from pages.trees import render
render("he")
""")
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(
            [button.label for button in app.button],
            ["עץ משפחה", "מקומות שביקרו בהם", "צאצאים", "שושלת המסורת"],
        )
        description = "\n".join(markdown.value for markdown in app.markdown)
        self.assertIn("הורים", description)
        self.assertIn("אבות קדומים", description)

    def test_home_tree_card_summarizes_all_views_and_opens_landing(self):
        app = AppTest.from_string("""
from pages.home import render
render("en")
""")
        with patch.object(home.navigation, "go") as go:
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual([button.label for button in app.button][-1], "Trees")
            description = "\n".join(markdown.value for markdown in app.markdown)
            self.assertNotIn("Explore four complementary", description)
            for tree_name in ("Family Tree", "Studied From", "Places Visited", "Descendants"):
                self.assertIn(tree_name, description)
            self.assertIn("View recorded parents, children", description)
            self.assertIn("Trace recorded parent-child paths", description)
            app.button[-1].click().run()
            go.assert_called_once_with(PAGE_TREES)
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
