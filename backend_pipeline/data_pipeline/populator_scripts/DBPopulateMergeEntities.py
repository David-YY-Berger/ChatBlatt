# bs"d
"""
DBPopulateMergeEntities - Merge duplicate entities that represent the same
real-world concept into a single canonical entity.

Driven by a directory of per-entity-type CSV files (entitys_to_merge/, sitting
alongside this script), one file per EntityType, named "<entityType>_to_merge.csv"
(e.g. person_to_merge.csv, place_to_merge.csv -- entityType.value.lower()). Each file
has columns:
    final_display_name, display_names_to_join, merged

  - final_display_name:     the canonical display name the merged entity should end up
                            with (e.g. "God").
  - display_names_to_join:  '|'-separated display_en_name values (case-insensitive) to
                            look up and merge together (e.g. "god|god hashem|hashem").
  - merged:                 "1" once this row has been successfully merged. Empty/"0"
                            means not yet merged. This column is re-written after every
                            row so an interrupted run never re-does already-completed work.

A type with nothing to merge yet simply doesn't need a CSV file -- missing files are
skipped silently; unrecognized files (not matching any EntityType) are logged and skipped.

Per row (skipped entirely if already marked merged):
  1. Every name in display_names_to_join is looked up (exact, case-insensitive match on
     display_en_name, restricted to the file's entityType). If any single name matches
     MORE THAN ONE entity, the name is ambiguous (display_en_name is not always unique
     even within one type) -- the row is logged and skipped so it can be resolved by
     hand; nothing is changed.
  2. If, across all names, fewer than 2 distinct entities were found there is nothing to
     merge (already a single entity, or nothing ingested yet) -- the row is skipped, and
     'merged' is left as-is so a future run (after more data is ingested) can re-check it.
  3. One matched entity becomes the surviving "target" (whichever already has
     display_en_name == final_display_name, else the first match in column order). Every
     other matched entity is a "duplicate" that gets merged into the target and removed.
  4. Duplicates are merged into the target ONE AT A TIME (see merge_scripts/EntityMerger.py):
     fold the duplicate's fields into the target and persist it, re-point every
     relationship and SourceMetadata reference from the duplicate's key to the target's
     key (dropping relationships that would become self-loops, de-duplicating against any
     relationship the target already has), then delete the duplicate entity. Because each
     duplicate is fully retired before the next one starts, an interrupted run never
     leaves a half-merged entity -- re-running the script simply picks up where it left off.
  5. The row is marked merged=1 and the CSV is re-written immediately.

Entry point: test_merge_entities (unittest-style, matching sibling populator scripts).
"""

import csv
import os
from typing import Dict, List, Set, Tuple

from backend.common import Paths
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass
from backend_pipeline.data_pipeline.populator_scripts.merge_scripts.EntityMerger import EntityMerger

MERGE_CSV_DIR = Paths.MERGE_CSV_DIR
CSV_FILENAME_SUFFIX = "_to_merge.csv"

FINAL_DISPLAY_NAME_COL = "final_display_name"
DISPLAY_NAMES_TO_JOIN_COL = "display_names_to_join"
MERGED_COL = "merged"
NAME_DELIMITER = "|"
MERGED_TRUE_VALUES = {"1", "true", "yes"}
_EMPTY_TALLIES = {"merged": 0, "already_merged": 0, "nothing_to_merge": 0, "ambiguous": 0, "error": 0}

class DBPopulateMergeEntities(DBParentClass):
    """Populator script that merges duplicate entities per entitys_to_merge/<entityType>_to_merge.csv."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    # ─── Entry point ───────────────────────────────────────────────────────────

    def test_merge_entities(self) -> None:
        """
        For every EntityType, look for entitys_to_merge/<entityType>_to_merge.csv
        (e.g. person_to_merge.csv, place_to_merge.csv) and merge each not-yet-merged
        row's entities. A type with nothing to merge yet simply doesn't need a file.
        """
        if not os.path.isdir(MERGE_CSV_DIR):
            print(f"No merge CSV directory found at {MERGE_CSV_DIR}.")
            return

        filename_to_type = {self._csv_filename_for_type(et): et for et in EntityType}
        grand_tallies = dict(_EMPTY_TALLIES)
        any_file_found = False

        for filename in sorted(os.listdir(MERGE_CSV_DIR)):
            file_path = os.path.join(MERGE_CSV_DIR, filename)
            if not os.path.isfile(file_path):
                continue

            entity_type = filename_to_type.get(filename.lower())
            if entity_type is None:
                print(f"[WARNING] '{filename}' does not match any '<entityType>_to_merge.csv' name, skipping.")
                continue

            any_file_found = True
            file_tallies = self._process_csv_file(file_path, entity_type)
            for status, count in file_tallies.items():
                grand_tallies[status] += count

        if not any_file_found:
            print(f"No '<entityType>_to_merge.csv' files found in {MERGE_CSV_DIR}.")
            return

        print(f"\n{'=' * 60}")
        print(
            f"MERGE SUMMARY (all types): merged={grand_tallies['merged']}, "
            f"already_merged={grand_tallies['already_merged']}, "
            f"nothing_to_merge={grand_tallies['nothing_to_merge']}, "
            f"ambiguous={grand_tallies['ambiguous']}, errors={grand_tallies['error']}"
        )
        print(f"{'=' * 60}")

    @staticmethod
    def _csv_filename_for_type(entity_type: EntityType) -> str:
        return f"{entity_type.value.lower()}{CSV_FILENAME_SUFFIX}"

    def _process_csv_file(self, csv_path: str, entity_type: EntityType) -> Dict[str, int]:
        """Process a single per-entity-type CSV file end-to-end; returns tallies for this file."""
        print(f"\n--- Processing {os.path.basename(csv_path)} (entityType={entity_type.value}) ---")
        rows, fieldnames = self._read_csv_rows(csv_path)
        tallies = dict(_EMPTY_TALLIES)
        if not rows:
            print(f"No rows found in {csv_path}.")
            return tallies

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
                status = self._process_row(final_display_name, row.get(DISPLAY_NAMES_TO_JOIN_COL) or "", entity_type)
            except Exception as e:
                print(f"[ERROR] '{final_display_name}': merge failed with an exception: {e}")
                status = "error"

            if status == "merged":
                row[MERGED_COL] = "1"
            tallies[status] = tallies.get(status, 0) + 1

            # Re-write progress after every row so an interrupted run never loses
            # already-merged rows (they stay marked merged=1 on disk).
            self._write_csv_rows(csv_path, fieldnames, rows)

        print(
            f"{os.path.basename(csv_path)} SUMMARY: merged={tallies['merged']}, "
            f"already_merged={tallies['already_merged']}, nothing_to_merge={tallies['nothing_to_merge']}, "
            f"ambiguous={tallies['ambiguous']}, errors={tallies['error']}"
        )
        return tallies

    # ─── Row-level merge logic ──────────────────────────────────────────────────

    def _process_row(self, final_display_name: str, names_field: str, entity_type: EntityType) -> str:
        """
        Attempt to merge one CSV row, with all lookups restricted to `entity_type`
        (the type implied by the file this row came from). Returns one of:
          "merged", "ambiguous", "nothing_to_merge".
        Unexpected DB errors propagate to the caller, which marks the row as "error".
        """
        names = self._parse_names(names_field)
        if not names:
            print(f"[ERROR] '{final_display_name}': no display_names_to_join provided, skipping.")
            return "nothing_to_merge"

        found_by_name: Dict[str, Entity] = {}
        for name in names:
            matches = self.db_api.get_entities_by_display_en_name(name, entity_type=entity_type)
            if len(matches) > 1:
                print(
                    f"[AMBIGUOUS] '{final_display_name}' ({entity_type.value}): name '{name}' matches "
                    f"{len(matches)} entities (keys={[m.key for m in matches]}); skipping this row for manual review."
                )
                return "ambiguous"
            if len(matches) == 1:
                found_by_name[name] = matches[0]

        # De-dupe by entity key (defensive; two distinct query strings can't really
        # resolve to the same doc since display_en_name is a single value per doc).
        entities = list({e.key: e for e in found_by_name.values()}.values())

        if len(entities) < 2:
            print(
                f"[SKIP] '{final_display_name}' ({entity_type.value}): only {len(entities)} distinct "
                f"entity(ies) found for {names}; nothing to merge."
            )
            return "nothing_to_merge"

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
        EntityMerger(self.db_api).merge_into_target(target, duplicates, final_display_name)

        print(
            f"[MERGED] '{final_display_name}' ({entity_type.value}): merged {len(duplicates)} duplicate(s) "
            f"{[d.key for d in duplicates]} into target key={target.key}."
        )
        return "merged"

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
        """
        Read a merge CSV. If the file doesn't start with the expected header (first
        column == 'final_display_name'), it's treated as headerless and that column
        order is assumed instead (with a warning), so an accidentally omitted header
        row doesn't silently swallow real data. Fully-blank rows (e.g. a trailing
        newline at EOF) are dropped. The file is rewritten with a proper header the
        next time _write_csv_rows runs.
        """
        default_fieldnames = [FINAL_DISPLAY_NAME_COL, DISPLAY_NAMES_TO_JOIN_COL, MERGED_COL]

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            first_line = next(csv.reader(f), None)
        has_header = bool(first_line) and first_line[0].strip().lower() == FINAL_DISPLAY_NAME_COL

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            if has_header:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or default_fieldnames)
            else:
                print(
                    f"[WARNING] '{os.path.basename(path)}': no header row detected (expected first "
                    f"column '{FINAL_DISPLAY_NAME_COL}'); assuming column order ({', '.join(default_fieldnames)})."
                )
                reader = csv.DictReader(f, fieldnames=default_fieldnames)
                fieldnames = default_fieldnames
            # Drop fully-blank rows (e.g. a trailing newline at EOF).
            rows = [dict(row) for row in reader if any((v or "").strip() for v in row.values())]

        return rows, fieldnames

    @staticmethod
    def _write_csv_rows(path: str, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
