import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "frontend"))
from components import layout
from translations1 import get_text


class LoadingLayoutTests(unittest.TestCase):
    def test_loading_label_is_localized_and_encoded_as_css_string(self):
        labels = []
        for lang in ("en", "he"):
            with self.subTest(lang=lang), patch.object(layout.st, "markdown") as markdown:
                layout.apply_layout(lang)
                css = markdown.call_args.args[0]
                label = get_text("ui.loading", lang)
                labels.append(label)
                self.assertIn(f"--loading-label: {json.dumps(label, ensure_ascii=False)};", css)
        self.assertNotEqual(*labels)


if __name__ == "__main__":
    unittest.main()
