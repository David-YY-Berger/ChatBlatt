# bs"d
"""
DBApplyMergeDecisions - merge persons according to the ticked review files written by
DBIdentifyPersonMergeCandidates. Decisions come from each family's consolidated confidence file.
Legacy decisions in detail chunks are used only when their group is absent from the confidence file.
Merges BY ENTITY KEY (EntityMerger), so same-named entities are no problem.

  - `merge` ticked           -> merged.
  - `dont merge` / both      -> never merged.
  - neither ticked           -> skipped, unless undecided_policy == "merge" ("merge everything except
                                what I ticked 'dont merge'") or its confidence exceeds its configured
                                kind's threshold. Even then, a group containing a pre-populated
                                person (book_references set - deliberately separate people) is skipped
                                unless it was explicitly ticked `merge`.
  - dry_run (default True)   -> only prints the plan; nothing is written. Set dry_run = False in setUp to apply.

Per group: all keys must still exist (else the group is stale -> skipped, e.g. an entity was already merged
via another group), target = entity named like the group label (else the one with most rels), final display
name = the label (the bare name for prefix groups). Safe to re-run: merged groups are stale afterwards.
For close-spelling groups the final name is an existing display name, not the normalized signature in the id.
"""

import glob
import os
from typing import Dict, List, Optional

from backend.common import Paths
from backend.models_db.Enums import RelType
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass
from backend_pipeline.data_pipeline.populator_scripts.merge_scripts import merge_candidates as mc
from backend_pipeline.data_pipeline.populator_scripts.merge_scripts.EntityMerger import EntityMerger


class DBApplyMergeDecisions(DBParentClass):
    __test__ = True

    def setUp(self):
        super().setUp()
        # ====== SAFETY: dry run unless explicitly switched off ======
        self.dry_run: bool = getattr(self, "dry_run", True)
        # ====== "skip" = merge only ticked groups; "merge" = merge all except dont-merge/conflict ======
        self.undecided_policy: str = getattr(self, "undecided_policy", mc.UNDECIDED_SKIP)
        self.confidence_thresholds: Dict[str, float] = getattr(self, "confidence_thresholds", {})
        # self.confidence_thresholds = {mc.KIND_CLOSE_SPELLING: 25}
        self.review_dir: str = getattr(self, "review_dir", Paths.MERGE_REVIEW_DIR)

    def test_apply_prefix_merge_decisions(self) -> None:
        confidence_path = os.path.join(
            self.review_dir, "prefix_matches", "confidence_person_prefix_matches.md"
        )
        with open(confidence_path, "r", encoding="utf-8") as f:
            parsed = mc.parse_confidence_file(f.read())

        non_prefix_groups = [
            group["id"] for group in parsed
            if not group["id"].startswith(f"{mc.KIND_PREFIX}:")
        ]
        if non_prefix_groups:
            raise ValueError(
                f"Prefix confidence file contains non-prefix group(s): {non_prefix_groups}"
            )
        self._apply_groups(parsed, confidence_path)

    def test_apply_prefix_merge_except_dont_merge(self) -> None:
        self.undecided_policy = mc.UNDECIDED_MERGE
        self.test_apply_prefix_merge_decisions()

    def test_apply_merge_decisions(self) -> None:
        self._apply_review_family(None)

    def test_apply_same_name_merge_decisions(self) -> None:
        self._apply_review_family(mc.KIND_SAME_NAME)

    def test_apply_close_spelling_merge_decisions(self) -> None:
        self._apply_review_family(mc.KIND_CLOSE_SPELLING)

    def _apply_review_family(self, kind: Optional[str]) -> None:
        parsed = []
        confidence_group_ids = set()
        for family, folder, file_prefix in (
            (mc.KIND_PREFIX, "prefix_matches", "person_prefix_matches"),
            (mc.KIND_SAME_NAME, "same_name_matches", "person_same_name_matches"),
            (mc.KIND_CLOSE_SPELLING, "close_spelling_matches", "person_close_spelling_matches"),
        ):
            if kind is not None and family != kind:
                continue
            confidence_path = os.path.join(
                self.review_dir, folder, f"confidence_{file_prefix}.md"
            )
            if os.path.exists(confidence_path):
                with open(confidence_path, "r", encoding="utf-8") as f:
                    confidence_groups = mc.parse_confidence_file(f.read())
                if kind is not None and any(not g["id"].startswith(f"{kind}:") for g in confidence_groups):
                    raise ValueError(f"{confidence_path} contains a non-{kind} group")
                parsed.extend(confidence_groups)
                confidence_group_ids.update(g["id"] for g in confidence_groups)

        file_pattern = f"person_{kind}_matches_*.md" if kind else "person_*_matches_*.md"
        pattern = os.path.join(self.review_dir, "**", file_pattern)
        for path in sorted(glob.glob(pattern, recursive=True)):
            with open(path, "r", encoding="utf-8") as f:
                parsed.extend(
                    g for g in mc.parse_review_file(f.read())
                    if not g["id"].startswith(f"{mc.KIND_PREFIX}:")
                    and (kind is None or g["id"].startswith(f"{kind}:"))
                    and g["id"] not in confidence_group_ids
                )
        self._apply_groups(parsed, f"{kind or 'all'} review files in {self.review_dir}")

    def _apply_groups(self, parsed: List[dict], source: str) -> None:
        if not parsed:
            print(f"No groups found in {source}.")
            return
        to_merge = mc.select_groups_to_merge(parsed, self.undecided_policy, self.confidence_thresholds)
        tallies: Dict[str, int] = {"merged": 0, "stale": 0, "protected": 0,
                                   "skipped": 0, "dry_run": 0, "error": 0}
        print(f"{len(parsed)} group(s) from {source}; {len(to_merge)} selected "
              f"(undecided_policy={self.undecided_policy}, "
              f"confidence_thresholds={self.confidence_thresholds}, dry_run={self.dry_run}).")

        merger = EntityMerger(self.db_api)
        for g in to_merge:
            label = g["id"].split(":", 1)[1]
            try:
                status = self._apply_group(merger, g, label)
            except EOFError:
                raise
            except Exception as e:
                print(f"[ERROR] {g['id']}: {e}")
                status = "error"
            tallies[status] += 1
        print(f"SUMMARY: {tallies}")

    def _apply_group(self, merger: EntityMerger, group: dict, label: str) -> str:
        entities = self.db_api.get_entities_by_keys(group["keys"])
        if len(entities) != len(set(group["keys"])) or len(entities) < 2:
            print(f"[STALE] {group['id']}: {len(entities)}/{len(set(group['keys']))} entities still exist; skipping.")
            return "stale"
        if group["decision"] == "undecided" and sum(1 for e in entities if e.book_references) > 0:
            print(f"[PROTECTED] {group['id']}: contains pre-populated person(s); tick `merge` explicitly to merge.")
            return "protected"

        if group["id"].startswith(f"{mc.KIND_CLOSE_SPELLING}:"):
            label = mc.close_spelling_label(entities)
        target = merger.choose_target(entities, label)
        duplicates = [e for e in entities if e.key != target.key]
        plan = f"{group['id']}: merge {[d.key for d in duplicates]} into {target.key} as '{label}'"
        keys = {e.key for e in entities}
        rels = self.db_api.get_rels_for_entities(list(keys))
        parent_types = (RelType.childOfFather, RelType.childOfMother)
        parent_keys = {
            rel_type: {r.term2 for r in rels if r.term1 in keys and r.rel_type == rel_type}
            for rel_type in parent_types
        }
        if any(parents & keys for parents in parent_keys.values()):
            print(f"[SKIPPED] {group['id']}: a group member is another member's parent; review manually.")
            return "skipped"
        conflicts = {rel_type: parents for rel_type, parents in parent_keys.items() if len(parents) > 1}
        if self.dry_run:
            print(f"[DRY RUN] {plan}")
            for rel_type, parents in conflicts.items():
                print(f"  Parent choice required for {rel_type.value}: {sorted(parents)}")
            return "dry_run"
        choices = self._choose_parents(group["id"], entities, rels, conflicts)
        if choices is None:
            print(f"[SKIPPED] {group['id']}: merge cancelled.")
            return "skipped"
        merger.merge_into_target(target, duplicates, label)
        if choices:
            for rel in self.db_api.get_rels_for_entity(target.key):
                if rel.term1 == target.key and rel.rel_type in choices and rel.term2 != choices[rel.rel_type]:
                    merger.delete_rel(rel)
        print(f"[MERGED] {plan}")
        return "merged"

    def _choose_parents(self, group_id, entities, rels, conflicts):
        if not conflicts:
            return {}

        parent_keys = {key for parents in conflicts.values() for key in parents}
        parent_rels = self.db_api.get_rels_for_entities(list(parent_keys))
        direct_types = (RelType.childOfFather, RelType.childOfMother)
        name_keys = parent_keys | {
            r.term2 for r in parent_rels if r.term1 in parent_keys and r.rel_type in direct_types
        } | {
            r.term2 for r in rels if r.term1 in {e.key for e in entities} and r.rel_type in direct_types
        }
        names = {e.key: e for e in self.db_api.get_entities_by_keys(list(name_keys))}

        def describe(entity, entity_rels):
            is_woman = getattr(entity, "isWoman", None)
            gender = "unknown" if is_woman is None else ("female" if is_woman else "male")
            time_period = getattr(entity, "timePeriod", None)
            period = getattr(time_period, "value", time_period) or "unknown"
            roles = ", ".join(str(getattr(role, "value", role))
                              for role in (getattr(entity, "roles", None) or [])) or "unknown"
            parents = []
            for rel in entity_rels:
                if rel.term1 == entity.key and rel.rel_type in direct_types:
                    parent = names.get(rel.term2)
                    parents.append(f"{rel.rel_type.value}: {parent.display_en_name if parent else 'unknown'} ({rel.term2})")
            return (f"{entity.display_en_name} ({entity.key}); period: {period}; roles: {roles}; "
                    f"gender: {gender}; parents: {', '.join(parents) or 'none recorded'}")

        print(f"\nParent conflicts for {group_id}. Candidates being merged:")
        for entity in entities:
            print(f"  {describe(entity, rels)}")
        selected = {}
        for rel_type, keys in conflicts.items():
            options = sorted(keys)
            print(f"\nChoose {rel_type.value}:")
            for number, key in enumerate(options, 1):
                parent = names.get(key)
                details = (describe(parent, parent_rels) if parent else
                           f"unknown entity ({key}); period: unknown; roles: unknown; gender: unknown; parents: unknown")
                print(f"  {number}. {details}")
            cancel = len(options) + 1
            print(f"  {cancel}. Never mind, don't merge")
            while True:
                answer = input("Enter a number: ").strip()
                if answer.isdigit() and 1 <= int(answer) <= cancel:
                    number = int(answer)
                    break
                print(f"Enter a number from 1 to {cancel}.")
            if number == cancel:
                return None
            selected[rel_type] = options[number - 1]
        return selected
