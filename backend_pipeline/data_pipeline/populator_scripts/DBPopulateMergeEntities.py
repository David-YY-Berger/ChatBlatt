# bs"d
"""
DBPopulateMergeEntities - Merge duplicate entities that represent the same
real-world concept into a single canonical entity.

Driven by a CSV file (entitys_to_merge.csv, sitting alongside this script) with columns:
    final_display_name, display_names_to_join, merged

  - final_display_name:     the canonical display name the merged entity should end up
                            with (e.g. "God").
  - display_names_to_join:  '|'-separated display_en_name values (case-insensitive) to
                            look up and merge together (e.g. "god|god hashem|hashem").
  - merged:                 "1" once this row has been successfully merged. Empty/"0"
                            means not yet merged. This column is re-written after every
                            row so an interrupted run never re-does already-completed work.

Per row (skipped entirely if already marked merged):
  1. Every name in display_names_to_join is looked up (exact, case-insensitive match on
     display_en_name). If any single name matches MORE THAN ONE entity, the name is
     ambiguous (display_en_name is not always unique) -- the row is logged and skipped so
     it can be resolved by hand; nothing is changed.
  2. If, across all names, fewer than 2 distinct entities were found there is nothing to
     merge (already a single entity, or nothing ingested yet) -- the row is skipped, and
     'merged' is left as-is so a future run (after more data is ingested) can re-check it.
  3. All matched entities must share the same entityType; a mix is logged and skipped.
  4. One matched entity becomes the surviving "target" (whichever already has
     display_en_name == final_display_name, else the first match in column order). Every
     other matched entity is a "duplicate" that gets merged into the target and removed.
  5. Duplicates are merged into the target ONE AT A TIME (see _merge_duplicate_into_target):
     fold the duplicate's fields into the target and persist it, re-point every
     relationship and SourceMetadata reference from the duplicate's key to the target's
     key (dropping relationships that would become self-loops, de-duplicating against any
     relationship the target already has), then delete the duplicate entity. Because each
     duplicate is fully retired before the next one starts, an interrupted run never
     leaves a half-merged entity -- re-running the script simply picks up where it left off.
  6. The row is marked merged=1 and the CSV is re-written immediately.

Entry point: test_merge_entities (unittest-style, matching sibling populator scripts).
"""

import csv
import os
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Rel import Rel
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entitys_to_merge.csv")

FINAL_DISPLAY_NAME_COL = "final_display_name"
DISPLAY_NAMES_TO_JOIN_COL = "display_names_to_join"
MERGED_COL = "merged"
NAME_DELIMITER = "|"
MERGED_TRUE_VALUES = {"1", "true", "yes"}

# Entity fields whose merge logic is special-cased in _fold_fields_into_target (name/alias
# bookkeeping); every other persisted field is merged generically via reflection.
_SPECIAL_CASED_FIELDS = {
    "key", "entityType", "display_en_name", "display_heb_name",
    "all_en_names", "all_heb_names", "alias_keys",
}


def _normalize_for_dedupe(item):
    """Normalize a list item for case/enum-insensitive de-duplication."""
    if isinstance(item, str):
        return item.lower()
    if isinstance(item, Enum):
        return item.value
    return item


def _merge_lists(*lists) -> list:
    """Union multiple lists together, de-duplicating (case/enum-insensitively) while
    preserving first-seen order and original casing."""
    seen = set()
    result = []
    for lst in lists:
        for item in (lst or []):
            if item is None or item == "":
                continue
            norm = _normalize_for_dedupe(item)
            if norm not in seen:
                seen.add(norm)
                result.append(item)
    return result


class DBPopulateMergeEntities(DBParentClass):
    """Populator script that merges duplicate entities per entitys_to_merge.csv."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    # ─── Entry point ───────────────────────────────────────────────────────────

    def test_merge_entities(self) -> None:
        """Read entitys_to_merge.csv and merge each not-yet-merged row's entities."""
        rows, fieldnames = self._read_csv_rows(CSV_PATH)
        if not rows:
            print(f"No rows found in {CSV_PATH}.")
            return

        tallies = {"merged": 0, "already_merged": 0, "nothing_to_merge": 0, "ambiguous": 0, "error": 0}

        for row in rows:
            final_display_name = (row.get(FINAL_DISPLAY_NAME_COL) or "").strip()

            if self._is_marked_merged(row):
                print(f"[ALREADY MERGED] '{final_display_name}' - skipping.")
                tallies["already_merged"] += 1
                continue

            if not final_display_name:
                print(f"[ERROR] Row missing '{FINAL_DISPLAY_NAME_COL}', skipping: {row}")
                tallies["error"] += 1
                continue

            try:
                status = self._process_row(final_display_name, row.get(DISPLAY_NAMES_TO_JOIN_COL) or "")
            except Exception as e:
                print(f"[ERROR] '{final_display_name}': merge failed with an exception: {e}")
                status = "error"

            if status == "merged":
                row[MERGED_COL] = "1"
            tallies[status] = tallies.get(status, 0) + 1

            # Re-write progress after every row so an interrupted run never loses
            # already-merged rows (they stay marked merged=1 on disk).
            self._write_csv_rows(CSV_PATH, fieldnames, rows)

        print(f"\n{'=' * 60}")
        print(
            f"MERGE SUMMARY: merged={tallies['merged']}, already_merged={tallies['already_merged']}, "
            f"nothing_to_merge={tallies['nothing_to_merge']}, ambiguous={tallies['ambiguous']}, "
            f"errors={tallies['error']}"
        )
        print(f"{'=' * 60}")

    # ─── Row-level merge logic ──────────────────────────────────────────────────

    def _process_row(self, final_display_name: str, names_field: str) -> str:
        """
        Attempt to merge one CSV row. Returns one of:
          "merged", "ambiguous", "nothing_to_merge", "type_mismatch".
        Unexpected DB errors propagate to the caller, which marks the row as "error".
        """
        names = self._parse_names(names_field)
        if not names:
            print(f"[ERROR] '{final_display_name}': no display_names_to_join provided, skipping.")
            return "nothing_to_merge"

        found_by_name: Dict[str, Entity] = {}
        for name in names:
            matches = self.db_api.get_entities_by_display_en_name(name)
            if len(matches) > 1:
                print(
                    f"[AMBIGUOUS] '{final_display_name}': name '{name}' matches {len(matches)} "
                    f"entities (keys={[m.key for m in matches]}); skipping this row for manual review."
                )
                return "ambiguous"
            if len(matches) == 1:
                found_by_name[name] = matches[0]

        # De-dupe by entity key (defensive; two distinct query strings can't really
        # resolve to the same doc since display_en_name is a single value per doc).
        entities = list({e.key: e for e in found_by_name.values()}.values())

        if len(entities) < 2:
            print(
                f"[SKIP] '{final_display_name}': only {len(entities)} distinct entity(ies) found "
                f"for {names}; nothing to merge."
            )
            return "nothing_to_merge"

        types = {e.entityType for e in entities}
        if len(types) > 1:
            print(
                f"[ERROR] '{final_display_name}': matched entities span multiple entity types "
                f"({sorted(t.value for t in types)}); skipping (cannot merge across types)."
            )
            return "type_mismatch"

        canonical_name = final_display_name.strip().lower()
        target = found_by_name.get(canonical_name)
        if target is None:
            for name in names:
                if name in found_by_name:
                    target = found_by_name[name]
                    break
        if target is None:
            # Can't happen given the len(entities) >= 2 check above, but guard anyway.
            raise RuntimeError(f"Could not determine a merge target for '{final_display_name}'.")

        duplicates = [e for e in entities if e.key != target.key]
        for dup in duplicates:
            self._merge_duplicate_into_target(target, dup, canonical_name, final_display_name)

        print(
            f"[MERGED] '{final_display_name}': merged {len(duplicates)} duplicate(s) "
            f"{[d.key for d in duplicates]} into target key={target.key}."
        )
        return "merged"

    def _merge_duplicate_into_target(self, target: Entity, dup: Entity, canonical_name: str, original_display_name: str) -> None:
        """
        Fully merge `dup` into `target`: fold dup's fields into target, re-point every
        relationship and SourceMetadata reference from dup's key to target's key, then
        delete dup. Each step is persisted immediately (not batched in-memory) so that if
        this raises partway through, the DB is left consistent: dup still fully exists as
        a valid, independent entity (nothing left dangling) and will simply be picked back
        up on the next run.
        """
        self._fold_fields_into_target(target, dup, canonical_name, original_display_name)
        self.db_api.update_entity(target)

        self._repoint_rels(target.key, dup.key)
        self._repoint_source_metadata_entity_key(target.key, dup.key)

        self.db_api.delete_entity_by_key(dup.key)

    @staticmethod
    def _fold_fields_into_target(target: Entity, dup: Entity, canonical_name: str, original_display_name: str) -> None:
        """
        Mutate `target` in place so it absorbs `dup`'s data:
          - display_en_name is set to the canonical (lowercased) name.
          - display_heb_name is filled in from dup if target doesn't have one.
          - all_en_names/all_heb_names/alias_keys are unioned (dup's own key is kept as
            an alias so old references to it remain traceable).
          - every other persisted field (subclass-specific, e.g. EPerson.roles,
            EPlace.placeType, ENumber.heb_unit, ...) is merged generically: lists are
            unioned, bools are OR'd, everything else fills in only if target's is empty.
        This is entity-subclass-agnostic (uses reflection), so it works for any Entity type.
        """
        target.display_en_name = canonical_name
        if not target.display_heb_name and dup.display_heb_name:
            target.display_heb_name = dup.display_heb_name

        target.all_en_names = _merge_lists(target.all_en_names, dup.all_en_names, [original_display_name])
        target.all_heb_names = _merge_lists(target.all_heb_names, dup.all_heb_names)
        target.alias_keys = _merge_lists(target.alias_keys, dup.alias_keys, [dup.key])

        for field_name in type(target).get_db_field_names():
            if field_name in _SPECIAL_CASED_FIELDS:
                continue
            target_value = getattr(target, field_name, None)
            dup_value = getattr(dup, field_name, None)
            if isinstance(target_value, list):
                setattr(target, field_name, _merge_lists(target_value, dup_value))
            elif isinstance(target_value, bool):
                setattr(target, field_name, bool(target_value) or bool(dup_value))
            elif not target_value and dup_value:
                setattr(target, field_name, dup_value)

    def _repoint_rels(self, target_key: str, dup_key: str) -> None:
        """
        Re-point every relationship referencing dup_key to reference target_key instead.
          - If re-pointing would create a self-loop (both sides end up as target_key,
            e.g. a rel directly between dup and target, or a pre-existing self-loop on
            dup), the relationship is dropped entirely.
          - Otherwise, try_insert_rel re-points it while de-duplicating against any
            equivalent relationship the target already has.
        Any SourceMetadata whose rel_keys referenced the old relationship key is updated
        to point at the new (or de-duplicated) key. The stale relationship is always removed.
        """
        for rel in self.db_api.get_rels_for_entity(dup_key):
            new_term1 = target_key if rel.term1 == dup_key else rel.term1
            new_term2 = target_key if rel.term2 == dup_key else rel.term2

            new_key: Optional[str] = None
            if new_term1 != new_term2:
                new_rel = Rel.create(rel_type=rel.rel_type, term1=new_term1, term2=new_term2)
                new_key = self.db_api.try_insert_rel(new_rel)

            self._repoint_source_metadata_rel_key(rel.key, new_key)
            self.db_api.delete_rel_by_key(rel.key)

    def _repoint_source_metadata_entity_key(self, target_key: str, dup_key: str) -> None:
        """Replace dup_key with target_key in every SourceMetadata.entity_keys that references it."""
        for sm in self.db_api.get_source_metadata_by_entity_key(dup_key):
            sm.entity_keys.discard(dup_key)
            sm.entity_keys.add(target_key)
            self.db_api.update_source_metadata(sm)

    def _repoint_source_metadata_rel_key(self, old_rel_key: str, new_rel_key: Optional[str]) -> None:
        """Replace old_rel_key with new_rel_key (or just remove it, if None) in every
        SourceMetadata.rel_keys that references it."""
        for sm in self.db_api.get_source_metadata_by_rel_key(old_rel_key):
            sm.rel_keys.discard(old_rel_key)
            if new_rel_key:
                sm.rel_keys.add(new_rel_key)
            self.db_api.update_source_metadata(sm)

    # ─── CSV helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_names(names_field: str) -> List[str]:
        """Split display_names_to_join on '|', normalize (strip+lower), drop empties/dupes."""
        seen: Set[str] = set()
        result: List[str] = []
        for raw_name in names_field.split(NAME_DELIMITER):
            name = raw_name.strip().lower()
            if name and name not in seen:
                seen.add(name)
                result.append(name)
        return result

    @staticmethod
    def _is_marked_merged(row: Dict[str, str]) -> bool:
        return (row.get(MERGED_COL) or "").strip().lower() in MERGED_TRUE_VALUES

    @staticmethod
    def _read_csv_rows(path: str) -> Tuple[List[Dict[str, str]], List[str]]:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or [FINAL_DISPLAY_NAME_COL, DISPLAY_NAMES_TO_JOIN_COL, MERGED_COL]
            # Drop fully-blank rows (e.g. a trailing newline at EOF).
            rows = [dict(row) for row in reader if any((v or "").strip() for v in row.values())]
        return rows, list(fieldnames)

    @staticmethod
    def _write_csv_rows(path: str, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
