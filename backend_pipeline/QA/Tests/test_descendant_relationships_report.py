import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from backend.db.Collections import CollectionObjs
from backend_pipeline.data_pipeline.one_time_scripts.display_db.descendant_relationships import (
    build_reports,
    export_reports,
)


class DescendantRelationshipsReportTests(unittest.TestCase):
    def setUp(self):
        self.entities = [
            {"key": "a", "entityType": "Person", "display_en_name": "Adam", "display_heb_name": "אדם"},
            {"key": "b", "entityType": "Person", "display_en_name": "Beth", "display_heb_name": "בת"},
            {"key": "c", "entityType": "Person", "display_en_name": "Carl", "display_heb_name": "קרל"},
            {"key": "d", "entityType": "Person", "display_en_name": "Dan"},
        ]
        self.rels = [
            {"term1": "b", "term2": "a", "rel_type": "descendantOf"},
            {"term1": "c", "term2": "a", "rel_type": "descendantOf"},
            {"term1": "c", "term2": "b", "rel_type": "descendantOf"},
        ]

    def test_descendants_and_ancestors_are_ranked_independently(self):
        reports = build_reports(self.entities, self.rels)
        descendants = reports["descendants.md"]
        ancestors = reports["ancestors.md"]
        self.assertLess(descendants.index("## Adam"), descendants.index("## Beth"))
        self.assertNotIn("## Carl", descendants)
        self.assertLess(ancestors.index("## Carl"), ancestors.index("## Beth"))
        self.assertNotIn("## Adam", ancestors)
        self.assertNotIn("## Dan", descendants)
        self.assertIn("**Descendants: 2**\n\n- Beth | בת | Person | key: b", descendants)
        self.assertIn("**Ancestors: 2**\n\n- Adam | אדם | Person | key: a", ancestors)
        self.assertIn("not inferred ancestry", ancestors)

    def test_missing_and_non_person_endpoints_fail(self):
        with self.assertRaisesRegex(ValueError, "missing entity"):
            build_reports(self.entities, [{"term1": "missing", "term2": "a"}])
        self.entities[1]["entityType"] = "Place"
        with self.assertRaisesRegex(ValueError, "non-person"):
            build_reports(self.entities, self.rels)

    def test_export_queries_descendant_of_and_overwrites_empty_reports(self):
        db = MagicMock()
        rels = MagicMock()
        entities = MagicMock()
        db.get_collection.side_effect = lambda collection: rels if collection == CollectionObjs.RELATIONS else entities
        rels.find.return_value = []
        entities.find.return_value = []
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "ancestors.md").write_text("stale", encoding="utf-8")
            export_reports(db, output)
            self.assertIn("0 people", (output / "ancestors.md").read_text(encoding="utf-8"))
            self.assertIn("0 people", (output / "descendants.md").read_text(encoding="utf-8"))
        self.assertEqual(rels.find.call_args.args[0], {"rel_type": {"$in": ["descendantOf"]}})


if __name__ == "__main__":
    unittest.main()
