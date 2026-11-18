import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from frontend.pages import home


class HomePageTests(unittest.TestCase):
    def test_mcp_callout_links_to_examples_and_setup_in_current_language(self):
        streamlit = MagicMock()
        streamlit.columns.return_value = [MagicMock() for _ in range(4)]
        streamlit.button.return_value = False

        with patch.object(home, "st", streamlit):
            home.render("en")

        callout = streamlit.info.call_args.args[0]
        self.assertIn("Query our database in natural language!", callout)
        self.assertIn(
            "/mcp_setup?lang=en#set-up-your-own-free-mcp",
            callout,
        )
        self.assertIn("/mcp_setup?lang=en#real-examples", callout)

    def test_mcp_callout_is_translated_and_preserves_hebrew_language(self):
        streamlit = MagicMock()
        streamlit.columns.return_value = [MagicMock() for _ in range(4)]
        streamlit.button.return_value = False

        with patch.object(home, "st", streamlit):
            home.render("he")

        callout = streamlit.info.call_args.args[0]
        self.assertIn("שאלו את מאגר המידע שלנו בשפה טבעית", callout)
        self.assertIn("/mcp_setup?lang=he#set-up-your-own-free-mcp", callout)
        self.assertIn("/mcp_setup?lang=he#real-examples", callout)


if __name__ == "__main__":
    unittest.main()
