import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.models_db.SourceClasses.SourceClass import SourceClass


class SefariaUrlTests(unittest.TestCase):
    def test_references(self):
        cases = {
            "TN_Genesis_0_1:1": "Genesis.1.1",
            "TN_Genesis_0_1:28–2:1": "Genesis.1.28-2.1",
            "TN_II Chronicles_0_1:1-4": "II_Chronicles.1.1-4",
            "BT_Berakhot_0_2a:10-13": "Berakhot.2a.10-13",
            "BT_Bava Batra_0_13b:9-14a:4": "Bava_Batra.13b.9-14a.4",
        }
        for key, ref in cases.items():
            with self.subTest(key=key):
                self.assertEqual(SourceClass(key).get_sefaria_url(), f"https://www.sefaria.org/{ref}")

    def test_invalid_or_mismatched_reference_has_no_link(self):
        for key in ("TN_Genesis_0_bad", "BT_Genesis_0_1:1", "TN_unknown_0_1:1"):
            with self.subTest(key=key), self.assertLogs("backend.models_db.SourceClasses.SourceClass", level="WARNING"):
                self.assertIsNone(SourceClass(key).get_sefaria_url())
