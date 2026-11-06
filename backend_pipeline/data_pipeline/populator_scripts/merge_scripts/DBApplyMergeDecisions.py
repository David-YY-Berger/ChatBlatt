# bs"d
"""
DBApplyMergeDecisions - merge persons according to the ticked review files written by
DBIdentifyPersonMergeCandidates. Prefix decisions come from the family's consolidated confidence file;
other decisions come from per-chunk review files. Merges BY ENTITY KEY (EntityMerger), so same-named entities are no problem.

  - `merge` ticked           -> merged.
  - `dont merge` / both      -> never merged.
  - neither ticked           -> skipped, unless undecided_policy == "merge" ("merge everything except
                                what I ticked 'dont merge'"). Even then, a group containing a pre-populated
                                person (book_references set - deliberately separate people) is skipped
                                unless it was explicitly ticked `merge`.
  - dry_run (default True)   -> only prints the plan; nothing is written. Set dry_run = False in setUp to apply.

Per group: all keys must still exist (else the group is stale -> skipped, e.g. an entity was already merged
via another group), target = entity named like the group label (else the one with most rels), final display
name = the label (the bare name for prefix groups). Safe to re-run: merged groups are stale afterwards.
"""

import glob
import os
from typing import Dict

from backend.common import Paths
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
        self.review_dir: str = getattr(self, "review_dir", Paths.MERGE_REVIEW_DIR)

    def test_apply_merge_decisions(self) -> None:
        parsed = []
        pattern = os.path.join(self.review_dir, "**", "person_*_matches_*.md")
        for path in sorted(glob.glob(pattern, recursive=True)):
            with open(path, "r", encoding="utf-8") as f:
                parsed.extend(g for g in mc.parse_review_file(f.read())
                              if not g["id"].startswith(f"{mc.KIND_PREFIX}:"))
        prefix_confidence_path = os.path.join(
            self.review_dir, "prefix_matches", "confidence_person_prefix_matches.md"
        )
        if os.path.exists(prefix_confidence_path):
            with open(prefix_confidence_path, "r", encoding="utf-8") as f:
                parsed.extend(mc.parse_confidence_file(f.read()))
        if not parsed:
            print(f"No review files / groups found in {self.review_dir}.")
            return

        to_merge = mc.select_groups_to_merge(parsed, self.undecided_policy)
        tallies: Dict[str, int] = {"merged": 0, "stale": 0, "protected": 0, "dry_run": 0, "error": 0}
        print(f"{len(parsed)} group(s) in review files; {len(to_merge)} selected "
              f"(undecided_policy={self.undecided_policy}, dry_run={self.dry_run}).")

        merger = EntityMerger(self.db_api)
        for g in to_merge:
            label = g["id"].split(":", 1)[1]
            try:
                status = self._apply_group(merger, g, label)
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

        target = merger.choose_target(entities, label)
        duplicates = [e for e in entities if e.key != target.key]
        plan = f"{group['id']}: merge {[d.key for d in duplicates]} into {target.key} as '{label}'"
        if self.dry_run:
            print(f"[DRY RUN] {plan}")
            return "dry_run"
        merger.merge_into_target(target, duplicates, label)
        print(f"[MERGED] {plan}")
        return "merged"
