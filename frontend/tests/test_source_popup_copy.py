import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from components.source_popup import source_popup_html


class SourcePopupCopyButtonTests(unittest.TestCase):
    def test_popup_copy_control_is_accessible_icon_only(self):
        popup = source_popup_html(
            "copy-test",
            "Genesis 1:1",
            "בראשית א׳:א׳",
            "<p>In the beginning</p>",
            "<p>בראשית</p>",
        )

        match = re.search(
            r'<button class="source-copy-btn"[^>]*>(.*?)</button>',
            popup,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        button = match.group(0)
        self.assertIn('aria-label="Copy"', button)
        self.assertIn('data-copy-failed-label="Copy failed"', button)
        self.assertTrue(match.group(1).startswith("<svg"))
        self.assertNotIn(">Copy<", button)

    def test_popup_uses_source_key_not_popup_id_for_sefaria(self):
        popup = source_popup_html(
            "popup-0", "Bava Batra", "", "", "", lang="he",
            sefaria_source_key="BT_Bava Batra_0_13b:9-14a:4",
        )
        self.assertIn('href="https://www.sefaria.org/Bava_Batra.13b.9-14a.4"', popup)
        self.assertIn('title="פתיחה בספריא"', popup)
        self.assertIn('target="_blank" rel="noopener noreferrer"', popup)


if __name__ == "__main__":
    unittest.main()
