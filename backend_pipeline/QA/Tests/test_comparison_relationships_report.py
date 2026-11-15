import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from backend.db.Collections import CollectionObjs
from backend_pipeline.data_pipeline.one_time_scripts.display_db.comparison_relationships import (
    build_reports,
    export_reports,
)


class ComparisonRelationshipsReportTests(unittest.TestCase):
    def setUp(self):
        self.entities = [
            {"key": "p1", "entityType": "Person", "display_en_name": "Adam", "display_heb_name": "אדם"},
            {"key": "p2", "entityType": "Person", "display_en_name": "Zed", "display_heb_name": "זד"},
            {"key": "a1", "entityType": "Animal", "display_en_name": "Lion", "display_heb_name": "אריה"},
            {"key": "p3", "entityType": "Person", "display_en_name": "Unrelated"},
        ]
        self.rels = [
            {"term1": "p2", "term2": "a1", "rel_type": "comparedTo"},
            {"term1": "a1", "term2": "p2", "rel_type": "contrastedWith"},
            {"term1": "p1", "term2": "p2", "rel_type": "AliasOf"},
            {"term1": "p1", "term2": "p1", "rel_type": "comparedTo"},
            {"term1": "p3", "term2": "p2", "rel_type": "spokeWith"},
        ]

    def test_both_directions_types_order_and_self_relationship(self):
        reports = build_reports(self.entities, self.rels)
        person = reports["Person"]
        self.assertLess(person.index("## Zed"), person.index("## Adam"))
        self.assertNotIn("Unrelated", person)
        zed, adam = person.split("## Adam")
        self.assertIn("**Relationships: 3**", zed)
        self.assertIn("### Compared to (1)\n\n- Lion | אריה | Animal | key: a1", zed)
        self.assertIn("### Contrasted with this entity (1)\n\n- Lion | אריה", zed)
        self.assertIn("### Has this entity as an alias (1)\n\n- Adam | אדם", zed)
        self.assertIn("**Relationships: 2**", adam)
        self.assertIn("### Compared to this entity (1)", adam)
        self.assertIn("### Alias of (1)", adam)
        self.assertIn("### Compared to this entity (1)\n\n- Zed | זד", reports["Animal"])
        self.assertIn("0 entities", reports["Plant"])

    def test_missing_entity_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "missing entity"):
            build_reports(self.entities, [{"term1": "p1", "term2": "missing", "rel_type": "AliasOf"}])

    def test_export_filters_database_and_rewrites_empty_type(self):
        db = MagicMock()
        rel_collection = db.get_collection.return_value
        entity_collection = MagicMock()
        db.get_collection.side_effect = lambda collection: (
            rel_collection if collection == CollectionObjs.RELATIONS else entity_collection
        )
        rel_collection.find.return_value = self.rels[:3]
        entity_collection.find.return_value = self.entities[:3]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "Plant.md").write_text("stale", encoding="utf-8")
            paths = export_reports(db, output)
            self.assertIn(output / "Person.md", paths)
            self.assertIn("0 entities", (output / "Plant.md").read_text(encoding="utf-8"))
            self.assertIn("Lion | אריה", (output / "Person.md").read_text(encoding="utf-8"))
        query = rel_collection.find.call_args.args[0]
        self.assertEqual(set(query["rel_type"]["$in"]), {"comparedTo", "contrastedWith", "AliasOf"})


if __name__ == "__main__":
    unittest.main()
