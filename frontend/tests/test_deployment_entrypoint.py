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
