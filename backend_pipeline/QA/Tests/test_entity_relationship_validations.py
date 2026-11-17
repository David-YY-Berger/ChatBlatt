import unittest

from backend_pipeline.QA.Validations.validate_entity_relationships import validate_relationships


class ValidateEntityRelationshipsTests(unittest.TestCase):
    def test_reports_parent_gender_mismatches_but_ignores_unknown_gender(self):
        entities = [
            {"key": "female", "display_en_name": "Female", "isWoman": True},
            {"key": "male", "display_en_name": "Male", "isWoman": False},
            {"key": "unknown", "display_en_name": "Unknown"},
        ]
        relationships = [
            {"key": "r1", "term1": "child1", "term2": "female", "rel_type": "childOfFather"},
            {"key": "r2", "term1": "child2", "term2": "male", "rel_type": "childOfMother"},
            {"key": "r3", "term1": "child3", "term2": "unknown", "rel_type": "childOfFather"},
        ]

        issues = validate_relationships(entities, relationships)

        self.assertEqual([issue.check for issue in issues], ["parent gender", "parent gender"])
        self.assertIn("r1", issues[0].message)
        self.assertIn("r2", issues[1].message)

    def test_reports_pairs_that_are_both_siblings_and_parent_child(self):
        entities = [{"key": key, "display_en_name": key} for key in ("a", "b", "shared-parent")]
        relationships = [
            {"key": "shared-a", "term1": "a", "term2": "shared-parent", "rel_type": "childOfFather"},
            {"key": "shared-b", "term1": "b", "term2": "shared-parent", "rel_type": "childOfFather"},
            {"key": "parent-child", "term1": "a", "term2": "b", "rel_type": "childOfMother"},
        ]

        issues = validate_relationships(entities, relationships)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].check, "family relationship")
        self.assertIn("share a parent", issues[0].message)

    def test_reports_reciprocal_parent_and_studied_from_relationships(self):
        entities = [{"key": key, "display_en_name": key} for key in ("a", "b")]
        relationships = [
            {"key": "a-parent-of-b", "term1": "b", "term2": "a", "rel_type": "childOfFather"},
            {"key": "b-parent-of-a", "term1": "a", "term2": "b", "rel_type": "childOfFather"},
            {"key": "a-studies-b", "term1": "a", "term2": "b", "rel_type": "studiedFrom"},
            {"key": "b-studies-a", "term1": "b", "term2": "a", "rel_type": "studiedFrom"},
        ]

        issues = validate_relationships(entities, relationships)

        self.assertEqual({issue.check for issue in issues}, {"family relationship", "reciprocal studiedFrom"})
        family_issue = next(issue for issue in issues if issue.check == "family relationship")
        self.assertIn("each entity is recorded as the other's parent", family_issue.message)


if __name__ == "__main__":
    unittest.main()
