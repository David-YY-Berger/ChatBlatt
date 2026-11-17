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

    def test_english_table_of_contents_links_to_each_section_and_copy_is_preserved(self):
        rendered = self._rendered_markdown("en")
        html = "\n".join(rendered)

        self.assertIn('href="#what-is-eitz-habina"', html)
        self.assertIn('href="#how-is-eitz-habina-different"', html)
        self.assertIn('href="#about-feyga-menuha"', html)
        self.assertIn('href="#about-the-author"', html)
        self.assertIn('id="what-is-eitz-habina"', html)
        self.assertIn("Since the Bar Ilan Responsa project (1967)", html)
        self.assertIn("EitzHabina@gmail.com", html)
        self.assertIn('lang="he"', html)
        self.assertIn('lang="en"', html)

    def test_hebrew_page_translates_section_links_and_main_content(self):
        rendered = self._rendered_markdown("he")
        html = "\n".join(rendered)

        self.assertIn("תוכן העניינים", html)
        self.assertIn("מהו עץ הבינה?", html)
        self.assertIn("עץ הבינה הוא גרף ידע", html)
        self.assertIn('id="about-feyga-menuha"', html)
        self.assertIn('href="#about-the-author"', html)
        self.assertIn("ספר בן איש חי - הקדמה", html)


if __name__ == "__main__":
    unittest.main()
