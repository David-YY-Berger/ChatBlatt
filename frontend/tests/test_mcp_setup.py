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
             patch.object(mcp_setup.metrics, "admin_params", return_value={}), \
             patch.object(mcp_setup.metrics, "is_testing_environment", return_value=False), \
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
        self.assertIn("**Sefaria links:**", rendered_markdown)
        self.assertIn(
            "**which people are recorded as having visited Tiberias?** "
            "List the sources and briefly explain the context.",
            streamlit.expander.call_args_list[0].args[0],
        )
        self.assertTrue(
            all("**" in call.args[0] for call in streamlit.expander.call_args_list)
        )
        self.assertIn(
            "Sukkah 27a–27b ([View in Sefaria](https://www.sefaria.org/Sukkah.27a-27b))",
            rendered_markdown,
        )
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
        self.assertEqual(
            [
                (call.args[0], call.kwargs["anchor"])
                for call in streamlit.subheader.call_args_list
            ],
            [
                ("What is an MCP?", "what-is-mcp"),
                ("Real examples", "real-examples"),
                ("Set up your own free MCP", "set-up-your-own-free-mcp"),
            ],
        )
        rendered_markdown = " ".join(
            str(call.args[0]) for call in streamlit.markdown.call_args_list
        )
        self.assertIn("[What is an MCP?](#what-is-mcp)", rendered_markdown)
        self.assertIn("[Real examples](#real-examples)", rendered_markdown)
        self.assertIn(
            "[Set up your own free MCP](#set-up-your-own-free-mcp)",
            rendered_markdown,
        )
        streamlit.image.assert_not_called()

    def test_hebrew_content_is_rtl_and_server_url_remains_ltr(self):
        streamlit = MagicMock()
        with patch.object(mcp_setup, "st", streamlit), \
             patch.object(mcp_setup.metrics, "admin_params", return_value={}), \
             patch.object(mcp_setup.metrics, "is_testing_environment", return_value=False), \
             patch.dict("os.environ", {"MCP_ENABLED": "true"}):
            mcp_setup.render("he")

        style = streamlit.markdown.call_args_list[0].args[0]
        self.assertIn(".st-key-mcp_page { direction: rtl; text-align: right; }", style)
        self.assertIn('[data-testid="stCodeBlock"] { direction: ltr; text-align: left; }', style)
        self.assertIn('[data-testid="stCode"] { direction: ltr; text-align: left; }', style)
        self.assertIn('[class*="st-key-mcp_example_answer_"] { direction: ltr; text-align: left; }', style)
        self.assertEqual(
            [call.kwargs["key"] for call in streamlit.container.call_args_list],
            ["mcp_page"] + [f"mcp_example_answer_{example}" for example in mcp_setup.SEFARIA_EXAMPLE_SOURCES],
        )
        self.assertEqual(streamlit.code.call_args.args[0], mcp_setup.MCP_URL)
        rendered_text = " ".join(
            str(call.args[0])
            for name in ("markdown", "subheader", "caption")
            for call in getattr(streamlit, name).call_args_list
        )
        self.assertIn("נסו הנחיה ופתחו כדי לראות את התשובה המלאה של Gemini", rendered_text)
        self.assertIn("התשובות המלאות מהשיחות המשותפות עם Gemini מוצגות באנגלית", rendered_text)
        rendered_markdown = " ".join(
            str(call.args[0]) for call in streamlit.markdown.call_args_list
        )
        self.assertIn("**קישורים לספריא:**", rendered_markdown)
        self.assertIn(
            "Sukkah 27a–27b ([לצפייה בספריא](https://www.sefaria.org/Sukkah.27a-27b))",
            rendered_markdown,
        )
        self.assertTrue(
            all(call.args[0].startswith("@Eitz Habina") for call in streamlit.expander.call_args_list)
        )

    def test_testing_url_is_available_only_in_admin_or_testing_mode(self):
        for admin, testing in ((False, False), (True, False), (False, True), (True, True)):
            for lang in ("en", "he"):
                with self.subTest(admin=admin, testing=testing, lang=lang):
                    streamlit = MagicMock()
                    params = {"admin": "true"} if admin else {"admin": "false"}
                    with patch.object(mcp_setup, "st", streamlit), \
                         patch.object(mcp_setup.metrics, "admin_params", return_value=params), \
                         patch.object(mcp_setup.metrics, "is_testing_environment", return_value=testing), \
                         patch.dict("os.environ", {"MCP_ENABLED": "true"}):
                        mcp_setup.render(lang)
                    expected = [call(mcp_setup.MCP_URL, language=None)]
                    if admin or testing:
                        expected.append(call(mcp_setup.MCP_TESTING_URL, language=None))
                    self.assertEqual(streamlit.code.call_args_list, expected)


if __name__ == "__main__":
    unittest.main()
