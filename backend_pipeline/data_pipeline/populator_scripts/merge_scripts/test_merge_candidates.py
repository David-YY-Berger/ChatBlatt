# bs"d
"""DB-free unit tests for merge_candidates (finding, rendering, parsing)."""

import unittest

from backend.models_db.EntityObjects.EPerson import EPerson
from backend.models_db.Enums import RelType, RoleType
from backend.models_db.Rel import Rel
from backend_pipeline.data_pipeline.populator_scripts.merge_scripts import merge_candidates as mc


def person(key, name):
    return EPerson(key=key, display_en_name=name)


class MergeCandidatesTest(unittest.TestCase):
    def setUp(self):
        self.people = [
            person("1", "akiva"), person("2", "Rabbi Akiva"), person("3", "rav akiva"),
            person("4", "joash"), person("5", "joash"), person("6", "moses"),
            person("7", "god"), person("8", "abba"),
        ]

    def test_split_prefix(self):
        self.assertEqual(mc.split_title_prefix("Rabbi  Akiva"), ("rabbi", "akiva"))
        self.assertEqual(mc.split_title_prefix("rabbinic"), (None, "rabbinic"))
        self.assertEqual(mc.split_title_prefix("abba"), (None, "abba"))

    def test_prefix_groups(self):
        groups, checked = mc.find_groups(self.people, mc.KIND_PREFIX, None)
        self.assertEqual([g.id for g in groups], ["prefix:akiva"])
        self.assertEqual(len(groups[0].entities), 3)
        self.assertEqual(checked, 8)

    def test_same_name_groups_and_limit(self):
        groups, _ = mc.find_groups(self.people, mc.KIND_SAME_NAME, None)
        self.assertEqual([g.id for g in groups], ["same_name:joash"])
        groups, checked = mc.find_groups(self.people, mc.KIND_SAME_NAME, 2)  # only 'abba', 'akiva' checked
        self.assertEqual((groups, checked), ([], 2))

    def test_chunking_never_splits_group(self):
        groups, _ = mc.find_groups(self.people, mc.KIND_PREFIX, None)
        groups += mc.find_groups(self.people, mc.KIND_SAME_NAME, None)[0]
        self.assertEqual([len(c) for c in mc.chunk_groups(groups, 4)], [1, 1])

    def test_render_warn_and_parse_roundtrip(self):
        groups, _ = mc.find_groups(self.people, mc.KIND_SAME_NAME, None)
        names = {p.key: p for p in self.people}
        rels = {"4": [Rel.create(RelType.childOfFather, "4", "7")], "5": []}
        text = mc.render_file("t", "d", groups, rels, names, 1, 1, 1)
        self.assertIn("GOD/HASHEM AS PARENT", text)
        self.assertEqual(mc.parse_review_file(text)[0]["decision"], "undecided")
        merged = text.replace("- [ ] merge", "- [x] merge")
        parsed = mc.parse_review_file(merged)
        self.assertEqual((parsed[0]["decision"], parsed[0]["keys"]), ("merge", ["4", "5"]))
        both = merged.replace("- [ ] dont merge", "- [X] dont merge")
        self.assertEqual(mc.parse_review_file(both)[0]["decision"], "conflict")

    def test_confidence_file_owns_prefix_decisions(self):
        groups, _ = mc.find_groups(self.people, mc.KIND_PREFIX, None)
        rated = mc.rate_groups(groups, {})
        text = mc.render_confidence_file("t", rated, {"prefix:akiva": "dont_merge"},
                                         include_decisions=True)
        parsed = mc.parse_confidence_file(text)
        self.assertEqual(parsed[0]["decision"], "dont_merge")
        self.assertEqual(mc.carry_over_decisions(groups, parsed), {"prefix:akiva": "dont_merge"})
        self.assertEqual(mc.select_groups_to_merge(parsed), [])
        self.assertIn("- [x] dont merge", text)

        names = {p.key: p for p in self.people}
        details = mc.render_file("t", "d", groups, {}, names, 1, 1, 1, include_decisions=False)
        self.assertNotIn("- [ ] merge", details)
        self.assertNotIn("- [ ] dont merge", details)

    def test_non_tanna_amora_role_forces_zero_confidence(self):
        groups, _ = mc.find_groups(self.people, mc.KIND_PREFIX, None)
        groups[0].entities[0].roles = [RoleType.Tanna]
        groups[0].entities[1].roles = [RoleType.Prophet]
        confidence, reasons = mc.rate_group(groups[0], {})
        self.assertEqual(confidence, 0)
        self.assertTrue(any("Prophet" in reason for reason in reasons))

    def test_confidence_sorted_and_parsed(self):
        groups, _ = mc.find_groups(self.people, mc.KIND_PREFIX, None)
        groups += mc.find_groups(self.people, mc.KIND_SAME_NAME, None)[0]
        rated = mc.rate_groups(groups, {"4": [Rel.create(RelType.childOfFather, "4", "6")],
                                        "5": [Rel.create(RelType.childOfFather, "5", "8")]})
        self.assertEqual([r["id"] for r in rated], ["prefix:akiva", "same_name:joash"])
        self.assertGreater(rated[0]["confidence"], rated[1]["confidence"])
        parsed = mc.parse_confidence_file(mc.render_confidence_file("t", rated))
        self.assertEqual([p["id"] for p in parsed], ["prefix:akiva", "same_name:joash"])
        self.assertTrue(all(p["decision"] == "undecided" for p in parsed))

    def test_carry_over_and_select(self):
        groups, _ = mc.find_groups(self.people, mc.KIND_SAME_NAME, None)
        names = {p.key: p for p in self.people}
        text = mc.render_file("t", "d", groups, {}, names, 1, 1, 1, {"same_name:joash": "dont_merge"})
        prev = mc.parse_review_file(text)
        self.assertEqual(prev[0]["decision"], "dont_merge")
        self.assertEqual(mc.carry_over_decisions(groups, prev), {"same_name:joash": "dont_merge"})
        self.assertEqual(mc.previous_decided_groups_not_in([], prev), prev)
        grown = groups[0].entities + [person("9", "joash")]
        grown_group = mc.Group(groups[0].id, groups[0].kind, groups[0].label, grown)
        self.assertEqual(mc.carry_over_decisions([grown_group], prev), {})  # membership changed -> re-review

        mixed = [{"id": "a", "decision": "merge"}, {"id": "b", "decision": "undecided"},
                 {"id": "c", "decision": "dont_merge"}, {"id": "d", "decision": "conflict"}]
        self.assertEqual([g["id"] for g in mc.select_groups_to_merge(mixed)], ["a"])
        self.assertEqual([g["id"] for g in mc.select_groups_to_merge(mixed, mc.UNDECIDED_MERGE)], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
