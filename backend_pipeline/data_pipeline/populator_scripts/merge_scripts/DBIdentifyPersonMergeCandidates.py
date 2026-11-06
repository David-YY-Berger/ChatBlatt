# bs"d
"""
DBIdentifyPersonMergeCandidates - READ-ONLY on the DB: scan EPerson entities for likely duplicates
and write markdown candidate details and confidence files for a human to decide. Prefix decisions live
in the consolidated confidence file; same-name decisions live in the chunk review files. Decisions are
applied by DBApplyMergeDecisions. Format + semantics: merge_candidates.py and
control_docs/pipeline/merge_entities.md. Output dir: Paths.MERGE_REVIEW_DIR.

Entry points (unittest-style, like the sibling populators):
  - test_identify_prefix_matches     -> prefix_matches/person_prefix_matches_NNN.md
        'akiva' / 'rabbi akiva' / 'rav akiva' (title prefixes: see merge_candidates.TITLE_PREFIXES)
  - test_identify_same_name_matches  -> same_name_matches/person_same_name_matches_NNN.md
        identical display_en_name; shows each entity's relationships, warns on God/Hashem parents
  - (close spelling hanna/hana/hannah: TBD)

Runtime knobs (set in setUp):
  - max_entities_to_check: only check the first N persons (sorted by name) as starting points;
    None = every person. Persons without any candidate are skipped and appear in no file.
  - max_entities_per_file: files are split so none has more than this many entities
    (a group is never split across files).

Re-running is SAFE for decisions: before rewriting a family's files, the existing files are read and
every `merge`/`dont merge` tick is carried into the new files if the group (same id AND same set of
entity keys) is still found. Previously ticked groups that this run's smaller scan did not
rediscover are kept as well (if all their entities still exist). A group whose membership changed
comes back undecided, on purpose. Files of the family are rewritten in place (renumbered).
"""

import glob
import os
from typing import Any, Dict, List, Optional

from backend.common import Paths
from backend.models_db.Enums import EntityType
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass
from backend_pipeline.data_pipeline.populator_scripts.merge_scripts import merge_candidates as mc

_KIND_INFO = {
    mc.KIND_PREFIX: (
        "prefix_matches",
        "person_prefix_matches",
        "Title-prefix matches (rabbi / rav / abba ...)",
        "Persons whose names are identical once a title prefix is removed (e.g. `akiva`, `rabbi akiva`, `rav akiva`). "
        "These are the most likely duplicates.",
    ),
    mc.KIND_SAME_NAME: (
        "same_name_matches",
        "person_same_name_matches",
        "Same exact display name",
        "Persons with the exact same display name (case-insensitive). Often genuinely different people "
        "(several Joashes) - compare the relationships below before deciding.",
    ),
}


class DBIdentifyPersonMergeCandidates(DBParentClass):
    __test__ = True

    def setUp(self):
        super().setUp()
        # ====== OPTIONAL: LIMIT TO FIRST N PERSONS (set None to check everyone) ======
        # self.max_entities_to_check: Optional[int] = getattr(self, "max_entities_to_check", 50)
        self.max_entities_to_check: Optional[int] = getattr(self, "max_entities_to_check", None)
        self.max_entities_per_file: int = getattr(self, "max_entities_per_file", mc.DEFAULT_MAX_ENTITIES_PER_FILE)
        self.output_dir: str = getattr(self, "output_dir", Paths.MERGE_REVIEW_DIR)

    def test_identify_prefix_matches(self) -> None:
        self._identify(mc.KIND_PREFIX)

    def test_identify_same_name_matches(self) -> None:
        self._identify(mc.KIND_SAME_NAME)

    def _identify(self, kind: str) -> None:
        persons = self.db_api.get_entities_by_type(EntityType.EPerson)
        groups, checked = mc.find_groups(persons, kind, self.max_entities_to_check)
        print(f"[{kind}] checked {checked}/{len(persons)} persons -> {len(groups)} candidate group(s).")

        folder_name, file_prefix, title, description = _KIND_INFO[kind]
        review_dir = os.path.join(self.output_dir, folder_name)
        os.makedirs(review_dir, exist_ok=True)
        old_files = sorted(glob.glob(os.path.join(review_dir, f"{file_prefix}_*.md")))
        legacy_files = sorted(glob.glob(os.path.join(self.output_dir, f"{file_prefix}_*.md")))
        confidence_path = os.path.join(review_dir, f"confidence_{file_prefix}.md")
        legacy_confidence_path = os.path.join(self.output_dir, f"confidence_{file_prefix}.md")

        previous: List[Dict[str, Any]] = []
        for path in old_files + legacy_files:
            with open(path, "r", encoding="utf-8") as f:
                previous.extend(mc.parse_review_file(f.read()))
        if kind == mc.KIND_PREFIX:
            for path in (confidence_path, legacy_confidence_path):
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        previous.extend(mc.parse_confidence_file(f.read()))
        decisions = mc.carry_over_decisions(groups, previous)
        kept_prev = mc.previous_decided_groups_not_in(groups, previous)
        kept_prev = list({p["id"]: p for p in kept_prev}.values())
        kept = self._revive_groups(kept_prev, kind)
        decisions.update({p["id"]: p["decision"] for p in kept_prev if p["id"] in {g.id for g in kept}})
        if kept:
            print(f"Keeping {len(kept)} previously decided group(s) not rediscovered by this scan.")
            groups = sorted(groups + kept, key=lambda g: g.id)
        print(f"Carried over {len(decisions)} existing decision(s).")

        chunks = mc.chunk_groups(groups, self.max_entities_per_file)
        written: List[str] = []
        group_number = 1
        all_rels: Dict[str, List[Any]] = {}
        for file_no, chunk in enumerate(chunks, 1):
            rels_by_entity, names = self._load_rels_and_names(chunk)
            all_rels.update(rels_by_entity)
            path = os.path.join(review_dir, f"{file_prefix}_{file_no:03d}.md")
            text = mc.render_file(title, description, chunk, rels_by_entity, names, file_no, len(chunks),
                                  group_number, decisions, include_decisions=kind != mc.KIND_PREFIX)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            written.append(path)
            group_number += len(chunk)

        for old in old_files + legacy_files:
            if old not in written:
                os.remove(old)

        if groups:
            rated = mc.rate_groups(groups, all_rels)
            with open(confidence_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(mc.render_confidence_file(title, rated, decisions,
                                                  include_decisions=kind == mc.KIND_PREFIX))
            print(f"Wrote {confidence_path}")
        elif os.path.exists(confidence_path):
            os.remove(confidence_path)
        if os.path.exists(legacy_confidence_path):
            os.remove(legacy_confidence_path)
        for path in written:
            print(f"Wrote {path}")
        if not written:
            print("No candidates found - nothing written.")

    def _revive_groups(self, previous_groups: List[Dict[str, Any]], kind: str) -> List[mc.Group]:
        """Rebuild previously decided groups from their keys; drop any whose entities are gone/<2."""
        revived: List[mc.Group] = []
        for p in previous_groups:
            found = self.db_api.get_entities_by_keys(p["keys"])
            if len(found) != len(set(p["keys"])) or len(found) < 2:
                continue
            revived.append(mc.Group(id=p["id"], kind=kind, label=p["id"].split(":", 1)[1],
                                    entities=mc.sorted_members(found)))
        return revived

    def _load_rels_and_names(self, groups: List[mc.Group]):
        """One rel query + one entity-name query per file (not per entity)."""
        keys = [e.key for g in groups for e in g.entities]
        rels = self.db_api.get_rels_for_entities(keys)
        rels_by_entity: Dict[str, List[Any]] = {k: [] for k in keys}
        for rel in rels:
            for k in {rel.term1, rel.term2}:
                if k in rels_by_entity:
                    rels_by_entity[k].append(rel)
        other_keys = {k for r in rels for k in (r.term1, r.term2)}
        names = {e.key: e for e in self.db_api.get_entities_by_keys(list(other_keys))}
        return rels_by_entity, names
