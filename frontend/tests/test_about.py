import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from pages.about import render


class AboutPageTests(unittest.TestCase):
    def _rendered_markdown(self, lang):
        with patch("pages.about.st.markdown") as markdown:
            render(lang)
        return [call.args[0] for call in markdown.call_args_list]

    def test_english_page_has_section_links_and_keeps_opening_quote_in_hebrew(self):
        rendered = self._rendered_markdown("en")
        html = "\n".join(rendered)

        self.assertIn('href="#what-is-eitz-habina"', html)
        self.assertIn('href="#how-is-eitz-habina-different"', html)
        self.assertIn('href="#about-feyga-menuha"', html)
        self.assertIn('href="#about-the-author"', html)
        self.assertIn('id="what-is-eitz-habina"', html)
        self.assertIn("Since the Bar-Ilan Responsa Project began in 1967", html)
        self.assertIn("EitzHabina@gmail.com", html)
        self.assertIn("https://www.linkedin.com/in/david-yy-berger/", html)
        self.assertIn(">in</span>", html)
        self.assertIn("### Compared with general-purpose AI assistants", html)
        self.assertEqual(html.count("**Pipeline**"), 1)
        self.assertNotIn("May the Creator be praised", html)
        self.assertIn("ספר בן איש חי - הקדמה", html)

    def test_hebrew_page_renders_hebrew_quote_and_translated_pipeline(self):
        rendered = self._rendered_markdown("he")
        html = "\n".join(rendered)

        self.assertIn("תוכן העניינים", html)
        self.assertIn("מהו עץ הבינה?", html)
        self.assertIn("בליבו נמצא גרף ידע", html)
        self.assertIn('id="about-feyga-menuha"', html)
        self.assertIn('href="#about-the-author"', html)
        self.assertIn("ספר בן איש חי - הקדמה", html)
        self.assertIn("צינור העיבוד", html)
        self.assertEqual(html.count("**צינור העיבוד**"), 1)
        self.assertIn("תפקיד שאינו תנא או אמורא מקבלת ציון 0%", html)
        self.assertIn("https://www.linkedin.com/in/david-yy-berger/", html)
        self.assertNotIn("May the Creator be praised", html)


if __name__ == "__main__":
    unittest.main()
