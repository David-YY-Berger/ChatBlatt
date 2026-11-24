import os
import sys
import unittest
from pathlib import Path
from unittest.mock import PropertyMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from streamlit.runtime.pages_manager import PagesManager
from streamlit.testing.v1 import AppTest
from streamlit.util import calc_md5

from frontend import app
import metrics


class DeploymentEntrypointTests(unittest.TestCase):
    def test_mcp_instructions_load_in_both_languages(self):
        for lang, expected in (("en", "What is an MCP?"), ("he", "מהו MCP?")):
            with self.subTest(lang=lang):
                test_app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
                test_app._page_hash = calc_md5("mcp_setup")
                test_app.session_state["lang"] = lang
                with patch.dict(os.environ, {"MCP_ENABLED": "true"}), \
                     patch.object(PagesManager, "uses_pages_directory", None):
                    test_app.run(timeout=30)
                self.assertFalse(test_app.exception)
                self.assertEqual(test_app.code[0].value, "https://eitz-habina-prod.up.railway.app/mcp")
                self.assertEqual(len(test_app.code), 1)
                self.assertEqual(test_app.subheader[0].value, expected)

    def test_mode_banners_and_testing_url_on_shared_mcp_page(self):
        for lang in ("en", "he"):
            for admin, testing in ((False, False), (True, False), (False, True), (True, True)):
                with self.subTest(lang=lang, admin=admin, testing=testing):
                    test_app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
                    test_app._page_hash = calc_md5("mcp_setup")
                    test_app.session_state["lang"] = lang
                    test_app.query_params["admin"] = "true" if admin else "false"
                    url = ("https://eitz-habina-testing.streamlit.app/mcp_setup"
                           if testing else "https://eitz-habina-prod.up.railway.app/mcp_setup")
                    with patch.dict(os.environ, {"MCP_ENABLED": "true"}), \
                         patch.object(PagesManager, "uses_pages_directory", None), \
                         patch.object(type(metrics.st.context), "url", new_callable=PropertyMock,
                                      return_value=url):
                        test_app.run(timeout=30)
                    self.assertFalse(test_app.exception)
                    warnings = [warning.value for warning in test_app.warning]
                    self.assertEqual(len(warnings), int(admin) + int(testing))
                    if admin:
                        self.assertIn(app.get_text("ui.admin_banner", lang), warnings)
                    if testing:
                        self.assertIn(app.get_text("ui.testing_banner", lang), warnings)
                    urls = [code.value for code in test_app.code]
                    self.assertEqual(len(urls), 2 if admin or testing else 1)
                    if admin or testing:
                        self.assertEqual(urls[1], app.mcp_setup.MCP_TESTING_URL)

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
