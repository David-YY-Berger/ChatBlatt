# bs"d
"""DB-free unit tests for merge_candidates (finding, rendering, parsing)."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

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

    def test_close_spelling_variants_and_word_boundaries(self):
        examples = [
            ("meir", "mer"),
            ("beiy", "bey", "bay", "bai"),
            ("yishai", "yishay", "yishey", "ishay", "yyishay"),
            ("hanna", "hana", "hannah", "hannahh"),
            ("megido", "meggido", "meggiddo", "megiddo"),
            ("michael", "mikhael"),
            ("yitzak", "itsak"),
            ("david", "dawid"),
            ("rabbi hannah ben meir", "rabbi hana ben mer"),
        ]
        for names in examples:
            with self.subTest(names=names):
                people = [person(str(i), name) for i, name in enumerate(names)]
                groups, checked = mc.find_groups(people, mc.KIND_CLOSE_SPELLING, None)
                self.assertEqual(checked, len(people))
                self.assertEqual(len(groups), 1)
                self.assertEqual({e.key for e in groups[0].entities}, {e.key for e in people})
                self.assertIn(groups[0].label, names)
                by_spelling = {mc.spelling_signature(names[0]): people}
                for start in people:
                    self.assertEqual(mc.close_spelling_group_for(start, by_spelling).id, groups[0].id)

        self.assertNotEqual(mc.spelling_signature("hannah"), mc.spelling_signature("hanah ben"))
        self.assertNotEqual(mc.spelling_signature("miriam"), mc.spelling_signature("moses"))
        self.assertNotEqual(mc.spelling_signature("ay"), mc.spelling_signature("a"))
        groups, _ = mc.find_groups([person("1", "Hana"), person("2", "hana")],
                                   mc.KIND_CLOSE_SPELLING, None)
        self.assertEqual(groups, [])

    def test_close_spelling_limit_and_decision_carryover(self):
        people = [person("1", "Hana"), person("2", "hannah"), person("3", "hanna")]
        groups, checked = mc.find_groups(people, mc.KIND_CLOSE_SPELLING, 1)
        self.assertEqual(checked, 1)
        self.assertEqual({e.key for e in groups[0].entities}, {"1", "2", "3"})
        text = mc.render_file("t", "d", groups, {}, {}, 1, 1, 1,
                              {groups[0].id: "merge"})
        previous = mc.parse_review_file(text)
        self.assertEqual(mc.carry_over_decisions(groups, previous), {groups[0].id: "merge"})
        self.assertIn("close spelling", mc.rate_group(groups[0], {})[1][-1])
        self.assertIn(f"Suggested final display name: `{groups[0].label}`", text)
        groups[0].entities.append(person("4", "hana"))
        self.assertEqual(mc.carry_over_decisions(groups, previous), {})

    def test_close_spelling_review_and_apply_use_real_name(self):
        from backend_pipeline.data_pipeline.populator_scripts.merge_scripts.DBApplyMergeDecisions import DBApplyMergeDecisions
        from backend_pipeline.data_pipeline.populator_scripts.merge_scripts.DBIdentifyPersonMergeCandidates import DBIdentifyPersonMergeCandidates

        people = [person("1", "Yishai"), person("2", "Ishey")]
        db = Mock()
        db.get_entities_by_type.return_value = people
        db.get_entities_by_keys.side_effect = lambda keys: [p for p in people if p.key in keys]
        db.get_rels_for_entities.return_value = []
        with TemporaryDirectory() as output_dir:
            identify = DBIdentifyPersonMergeCandidates("test_identify_close_spelling_matches")
            identify.db_api = db
            identify.output_dir = output_dir
            identify.max_entities_to_check = None
            identify.max_entities_per_file = 100
            identify.test_identify_close_spelling_matches()
            review = Path(output_dir) / "close_spelling_matches" / "person_close_spelling_matches_001.md"
            review.write_text(review.read_text(encoding="utf-8").replace("- [ ] merge", "- [x] merge"),
                              encoding="utf-8")
            identify.test_identify_close_spelling_matches()
            self.assertEqual(mc.parse_review_file(review.read_text(encoding="utf-8"))[0]["decision"], "merge")
            identify.max_entities_to_check = 0
            identify.test_identify_close_spelling_matches()
            review_text = review.read_text(encoding="utf-8")
            self.assertEqual(mc.parse_review_file(review_text)[0]["decision"], "merge")
            self.assertIn("Suggested final display name: `ishey`", review_text)

            apply = DBApplyMergeDecisions("test_apply_merge_decisions")
            apply.db_api = db
            apply.review_dir = output_dir
            apply.undecided_policy = mc.UNDECIDED_SKIP
            apply.dry_run = False
            with patch("backend_pipeline.data_pipeline.populator_scripts.merge_scripts.DBApplyMergeDecisions.EntityMerger") as merger_class:
                merger = merger_class.return_value
                merger.choose_target.return_value = people[1]
                apply.test_apply_merge_decisions()
                merger.choose_target.assert_called_once_with(people, "ishey")
                merger.merge_into_target.assert_called_once_with(people[1], [people[0]], "ishey")

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
