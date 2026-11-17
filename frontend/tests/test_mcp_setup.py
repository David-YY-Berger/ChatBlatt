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
        self.assertNotIn("admin", rendered_text.lower())
        self.assertNotIn("admin=true", rendered_text.lower())
        self.assertGreaterEqual(rendered_text.count("@Eitz Habina"), 8)
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
        self.assertEqual(streamlit.code.call_args.args[0], mcp_setup.MCP_URL)
        rendered_text = " ".join(
            str(call.args[0])
            for name in ("markdown", "subheader", "caption")
            for call in getattr(streamlit, name).call_args_list
        )
        self.assertGreaterEqual(rendered_text.count("@Eitz Habina"), 8)


if __name__ == "__main__":
    unittest.main()
