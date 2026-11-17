import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from streamlit.runtime.pages_manager import PagesManager
from streamlit.testing.v1 import AppTest
from streamlit.util import calc_md5

from frontend import app


class DeploymentEntrypointTests(unittest.TestCase):
    def test_mcp_instructions_load_in_both_languages(self):
        for lang, expected in (("en", "Connect your AI chat"), ("he", "חיבור לצ׳אט בינה מלאכותית")):
            with self.subTest(lang=lang):
                test_app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
                test_app._page_hash = calc_md5("mcp_setup")
                test_app.session_state["lang"] = lang
                with patch.dict(os.environ, {"MCP_ENABLED": "true"}), \
                     patch.object(PagesManager, "uses_pages_directory", None):
                    test_app.run(timeout=30)
                self.assertFalse(test_app.exception)
                self.assertEqual(test_app.code[0].value, "https://eitz-habina-prod.up.railway.app/mcp")
                self.assertEqual(
                    test_app.code[1].value,
                    "https://eitz-habina-prod.up.railway.app/mcp?admin=true",
                )
                self.assertEqual(test_app.subheader[0].value, expected)

    def test_disabled_mcp_page_shows_unavailable_in_both_languages(self):
        for lang in ("en", "he"):
            with self.subTest(lang=lang):
                test_app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
                test_app._page_hash = calc_md5("mcp_setup")
                test_app.session_state["lang"] = lang
                with patch.dict(os.environ, {"MCP_ENABLED": "false"}), \
                     patch.object(PagesManager, "uses_pages_directory", None):
                    test_app.run(timeout=30)
                self.assertFalse(test_app.exception)
                self.assertEqual(len(test_app.warning), 1)
                self.assertFalse(test_app.code)

    def test_home_load_runs_shared_app(self):
        test_app = AppTest.from_file(str(ROOT / "streamlit_app.py"))

        with patch.object(PagesManager, "uses_pages_directory", None), \
             patch.object(app.home, "render") as render:
            test_app.run(timeout=30)
            self.assertFalse(test_app.exception)
            self.assertFalse(PagesManager.uses_pages_directory)
            render.assert_called_once_with("en")

    def test_direct_page_load_runs_shared_app_before_renderer(self):
        test_app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
        test_app._page_hash = calc_md5("source_search")

        with patch.object(PagesManager, "uses_pages_directory", None), \
             patch.object(app.source_search, "render") as render:
            test_app.run(timeout=30)
            self.assertFalse(test_app.exception)
            self.assertFalse(PagesManager.uses_pages_directory)
            render.assert_called_once_with("en")


if __name__ == "__main__":
    unittest.main()
