import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontend.pages import mcp_setup


class McpSetupTests(unittest.TestCase):
    def test_page_only_shows_the_standard_server_url(self):
        streamlit = MagicMock()
        with patch.object(mcp_setup, "st", streamlit), \
             patch.dict("os.environ", {"MCP_ENABLED": "true"}):
            mcp_setup.render("en")

        self.assertEqual(
            streamlit.code.call_args_list,
            [call(mcp_setup.MCP_URL, language=None)],
        )
        rendered_text = " ".join(
            str(call.args[0])
            for name in ("markdown", "subheader", "caption")
            for call in getattr(streamlit, name).call_args_list
        )
        self.assertNotIn("admin=true", rendered_text.lower())
        self.assertIn("Try a prompt to see the full Gemini answer", rendered_text)
        self.assertIn("Full answers from the shared Gemini chats", rendered_text)
        self.assertEqual(streamlit.expander.call_count, 7)
        self.assertTrue(
            all(call.args[0].startswith("@Eitz Habina") for call in streamlit.expander.call_args_list)
        )
        rendered_markdown = " ".join(
            str(call.args[0]) for call in streamlit.markdown.call_args_list
        )
        self.assertIn("Eitz Habina records **13 people**", rendered_markdown)
        self.assertIn("**Soulmates:**", rendered_markdown)
        self.assertIn("15. **Lost Train of Thought", rendered_markdown)
        self.assertIn("Here are the key biblical prophecies", rendered_markdown)
        self.assertIn("### Children of King David", rendered_markdown)
        self.assertTrue(
            all(
                f"https://share.gemini.google/{chat_id}" in rendered_markdown
                for chat_id in (
                    "qVSh4WzowedW",
                    "bcizArvSiCVo",
                    "HwGJTvmIafug",
                    "AbJuQxcYd4NN",
                    "ezmiyUw5TI3S",
                    "P7ieEWnCcoLp",
                    "berPNzSE30Ni",
                )
            )
        )
        self.assertEqual(streamlit.image.call_args.args[0], mcp_setup.MCP_SCREENSHOT)
        self.assertTrue(mcp_setup.MCP_SCREENSHOT.is_file())

    def test_hebrew_content_is_rtl_and_server_url_remains_ltr(self):
        streamlit = MagicMock()
        with patch.object(mcp_setup, "st", streamlit), \
             patch.dict("os.environ", {"MCP_ENABLED": "true"}):
            mcp_setup.render("he")

        style = streamlit.markdown.call_args_list[0].args[0]
        self.assertIn(".st-key-mcp_page { direction: rtl; text-align: right; }", style)
        self.assertIn('[data-testid="stCodeBlock"] { direction: ltr; text-align: left; }', style)
        self.assertIn('[data-testid="stCode"] { direction: ltr; text-align: left; }', style)
        self.assertEqual(streamlit.code.call_args.args[0], mcp_setup.MCP_URL)
        rendered_text = " ".join(
            str(call.args[0])
            for name in ("markdown", "subheader", "caption")
            for call in getattr(streamlit, name).call_args_list
        )
        self.assertIn("נסו הנחיה ופתחו כדי לראות את התשובה המלאה של Gemini", rendered_text)
        self.assertIn("התשובות המלאות מהשיחות המשותפות עם Gemini מוצגות באנגלית", rendered_text)
        self.assertTrue(
            all(call.args[0].startswith("@Eitz Habina") for call in streamlit.expander.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
