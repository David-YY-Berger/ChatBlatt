import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

import app
from translations1 import get_text


class FooterTests(unittest.TestCase):
    def test_footer_renders_localized_copyright_notice(self):
        for lang in ("en", "he"):
            with self.subTest(lang=lang), patch("app.st.markdown") as markdown:
                app._render_footer(lang)

            rendered = markdown.call_args.args[0]
            self.assertIn('<footer class="app-footer"', rendered)
            self.assertIn(get_text("app.copyright", lang), rendered)
            self.assertIn("© 2026", rendered)


if __name__ == "__main__":
    unittest.main()
