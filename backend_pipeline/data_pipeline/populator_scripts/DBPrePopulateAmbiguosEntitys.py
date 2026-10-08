# bs"d
import json
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.common import Paths
from backend.db.Collections import CollectionObjs
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.EntityObjects.EPerson import EPerson
from backend.models_db.EntityObjects.EPlace import EPlace
from backend.models_db.EntityObjects.ETribeOfIsrael import ETribeOfIsrael
from backend.models_db.Enums import EntityType, RelType, TimePeriod
from backend.models_db.Rel import Rel
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass
from backend_pipeline.data_pipeline.PydanticModels.entity_rel_graph.erg_constants import TRIBES_OF_ISRAEL

# Fields (besides 'description' and 'id') that hold person/place names which must be
# validated against the source-content corpus. Boolean flags (isWoman, isNonJew) and
# bookReferences (book names, not passage text) are intentionally excluded.
# See Notes/entity_prepopulation_guide.md §2.2 for the full input-file field description.
NAME_FIELDS: List[str] = [
    "name",
    "all_en_names",
    "childOfFather",
    "childOfMother",
    "children",
    "spouseOf",
    "siblings",
    "associatedWithPlace",
    "diedIn",
    "tribeOfIsrael",
]

# How many successfully-validated names to buffer before printing them as one block
# (printing one line per name would be far too slow over hundreds/thousands of names).
LOG_BUFFER_SIZE = 100

# Names that are known-valid but intentionally not expected to appear verbatim in the
# source corpus (e.g. regnal-number disambiguators like "Jeroboam II" that distinguish
# entries sharing a name but are never written that way in the text itself). Skipped
# during the "not found in corpus" check.
IGNORED_NAMES: List[str] = [
    "Jeroboam I",
    "Jeroboam II",
]

# ─── Reference-resolution (§2.5 of the guide) ──────────────────────────────────────────

# Person-to-person reference fields that create a Rel once resolved.
ACTIONABLE_REL_FIELDS: List[str] = ["childOfFather", "childOfMother", "children", "spouseOf"]

# "siblings" is intentionally NOT in ACTIONABLE_REL_FIELDS - there is no sibling RelType
# (the UI derives siblings from shared parents - see guide §1.1/§2.3). References in this
# field are only resolved for the report, never turned into a Rel.
SIBLINGS_FIELD = "siblings"

# Person reference field -> the field(s), on a CANDIDATE entry, that would reciprocally
# name this entry back if the candidate is really the right match. E.g. if entry A lists
# "childOfFather": ["X"] and candidate X's own "children" list names A back, that is strong
# evidence X is the right match among several same-named candidates.
_RECIPROCAL_FIELDS: Dict[str, List[str]] = {
    "childOfFather": ["children"],
    "childOfMother": ["children"],
    "children": ["childOfFather", "childOfMother"],
    "spouseOf": ["spouseOf"],
}

# Rel type for each actionable field, where the direction does not depend on the entry's
# isWoman flag (childOfFather/childOfMother/spouseOf). "children" is handled separately
# since its Rel direction/type depends on whether THIS entry isWoman.
_FIELD_TO_REL_TYPE: Dict[str, RelType] = {
    "childOfFather": RelType.childOfFather,
    "childOfMother": RelType.childOfMother,
    "spouseOf": RelType.spouseOf,
}

# Place/tribe reference fields -> (RelType, Entity subclass) used to create or find the
# referenced place/tribe and link it to the entry. No ambiguity resolution applies here -
# places/tribes are looked up by exact name (see Entity.build_existence_query).
_PLACE_FIELDS: Dict[str, RelType] = {
    "associatedWithPlace": RelType.associatedWithPlace,
    "diedIn": RelType.diedIn,
}
TRIBE_FIELD = "tribeOfIsrael"


class DBPrePopulateAmbiguosEntitys(DBParentClass):
    """
    Pre-populates well-known, name-ambiguous entities (Tanach characters for now, Talmud
    sages later) into the entity graph, before any source is populated — so that people who
    share a name (e.g. two kings named Joash) end up as separate entities. See
    Notes/entity_prepopulation_guide.md for the full design.

    Currently only the name-validation pass is implemented (more to follow).
    """

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    # ─── Entry point ────────────────────────────────────────────────────────

    def test_validate_names(self) -> None:
        """
        Standalone validation pass over Paths.AMBIGUOUS_TANACH_CHARACTERS_JSON:
          - every NAME_FIELDS field present on an entry must be well-formed: a non-empty
            string, or a list of non-empty strings.
          - every name found must appear, in exact spelling, somewhere in the combined
            clean English text of all source contents currently in the DB.
        Every validated name is logged (buffered, flushed every LOG_BUFFER_SIZE names, to
        keep this fast); every missing/invalid field is logged immediately. Ends with a
        clear summary confirming the run completed.
        """
        entries = self._load_entries(Paths.AMBIGUOUS_TANACH_CHARACTERS_JSON)
        print(f"Loaded {len(entries)} entries from {Paths.AMBIGUOUS_TANACH_CHARACTERS_JSON}")

        corpus = self._build_source_corpus()
        print(f"Built source-content corpus: {len(corpus):,} characters.")

        log_buffer: List[str] = []
        names_checked = 0
        names_valid = 0
        issues: List[str] = []
        not_found: List[str] = []

        for entry in entries:
            entry_id = entry.get("id", "<no id>")

            for field in NAME_FIELDS:
                if field not in entry:
                    continue  # optional field, not present on this entry - nothing to check

                names = self._normalize_field_value(entry[field])

                if names is None:
                    issue = (
                        f"[ISSUE] id='{entry_id}' field='{field}' -> invalid type "
                        f"({type(entry[field]).__name__}), expected str or list[str]"
                    )
                    issues.append(issue)
                    print(issue)
                    continue

                if not names:
                    issue = f"[ISSUE] id='{entry_id}' field='{field}' -> empty value"
                    issues.append(issue)
                    print(issue)
                    continue

                for name in names:
                    if not isinstance(name, str) or not name.strip():
                        names_checked += 1
                        issue = f"[ISSUE] id='{entry_id}' field='{field}' -> blank/invalid entry in list"
                        issues.append(issue)
                        print(issue)
                        continue

                    for alt_name in self._split_alt_names(name):
                        names_checked += 1
                        if alt_name in IGNORED_NAMES:
                            names_valid += 1
                            continue
                        if alt_name in corpus:
                            names_valid += 1
                            # log_buffer.append(
                            #     f"[OK] id='{entry_id}' field='{field}' name='{alt_name}' -> found in corpus"
                            # )
                            if len(log_buffer) >= LOG_BUFFER_SIZE:
                                print("\n".join(log_buffer))
                                log_buffer.clear()
                        else:
                            issue = (
                                f"[ISSUE] id='{entry_id}' field='{field}' name='{alt_name}' -> "
                                f"NOT found (exact spelling) in any source content"
                            )
                            issues.append(issue)
                            not_found.append(issue)
                            print(issue)

        if log_buffer:
            print("\n".join(log_buffer))
            log_buffer.clear()

        print(f"\n{'=' * 60}")
        print("NOT FOUND IN CORPUS (exact spelling missing from all source content)")
        print(f"{'=' * 60}")
        if not_found:
            print("\n".join(not_found))
        else:
            print("(none - every name was found)")

        print(f"\n{'=' * 60}")
        print("VALIDATION COMPLETE")
        print(f"Entries processed:  {len(entries)}")
        print(f"Names checked:      {names_checked}")
        print(f"Names valid:        {names_valid}")
        print(f"Issues found:       {len(issues)}")
        print(f"Not found in corpus:{len(not_found):>5}")
        print(f"{'=' * 60}")

    # ─── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _load_entries(file_path: str) -> List[Dict[str, Any]]:
        """Load the input JSON file as a list of entity dicts."""
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON list of entries in {file_path}, got {type(data).__name__}")
        return data

    def _build_source_corpus(self) -> str:
        """
        Combine the clean English text of every TN + BT source content currently in the DB
        into a single string, used to confirm a name appears somewhere verbatim.
        """
        texts: List[str] = []
        for collection in (CollectionObjs.TN, CollectionObjs.BT):
            src_contents = self.db_api.get_all_src_contents_of_collection(collection)
            texts.extend(src.get_clean_en_text() for src in src_contents)
        return "\n".join(texts)

    @staticmethod
    def _normalize_field_value(value: Any) -> Optional[List[str]]:
        """Normalize a field's raw value to a list of strings, or None if the type is invalid."""
        if isinstance(value, str):
            return [value]
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return value
        return None

    @staticmethod
    def _split_alt_names(name: str) -> List[str]:
        """
        Split an "A / B" alternate-spelling reference (e.g. "Gideon / Jerubbaal") into its
        individual name candidates, so each spelling is checked against the corpus on its
        own. These free-text references (to people/places not necessarily defined as their
        own entry in this file) are resolved later by the disambiguation matching algorithm
        (Notes/entity_prepopulation_guide.md §2.5) using whichever form a passage happens to
        use — they are not expected to match the corpus as one combined string.
        """
        parts = [p.strip() for p in name.split("/")]
        return [p for p in parts if p]

    # ─────────────────────────────────────────────────────────────────────────────────
    # ─── Pre-population (Notes/entity_prepopulation_guide.md §2) ──────────────────────
    # ─────────────────────────────────────────────────────────────────────────────────

    # ─── Entry points ───────────────────────────────────────────────────────────────

    def test_print_prepopulation_report(self) -> None:
        """
        SAFE, read-only dry run: loads the input file, computes the full reference-
        resolution plan (no DB writes) and prints the report described in guide §2.7,
        plus a read-only pre-flight check against the DB for unexpectedly pre-existing
        same-named people. Review this before ever calling test_run_prepopulation.
        """
        file_path = Paths.AMBIGUOUS_TANACH_CHARACTERS_JSON
        entries = self._load_entries(file_path)
        plan = self._compute_plan(entries)
        preflight_issues = self._preflight_check(entries, plan, file_path)
        self._print_plan_report(entries, plan, preflight_issues)

    def test_run_prepopulation(self) -> None:
        """
        Entry point for the Tanach-characters file. Pre-populates every entry as its own
        EPerson (TimePeriod.Tanach), then resolves every person/place/tribe reference and
        writes the corresponding relationships. Idempotent - safe to re-run (see
        _progress_path/_load_progress/_save_progress and guide §2.6).
        """
        self._prepopulate(Paths.AMBIGUOUS_TANACH_CHARACTERS_JSON, TimePeriod.Tanach)

    # ─── Orchestration ──────────────────────────────────────────────────────────────

    def _prepopulate(self, file_path: str, default_time_period: TimePeriod) -> None:
        entries = self._load_entries(file_path)
        plan = self._compute_plan(entries)
        preflight_issues = self._preflight_check(entries, plan, file_path)
        self._print_plan_report(entries, plan, preflight_issues)

        if preflight_issues:
            print(f"\n{'=' * 60}\nABORTING: {len(preflight_issues)} pre-flight issue(s) found - see above. "
                  f"Resolve them (or clear the conflicting data) before running this again.\n{'=' * 60}")
            return

        progress = self._load_progress(file_path)
        person_stats = self._run_person_pass(entries, default_time_period, progress, file_path)
        ref_stats = self._run_reference_pass(entries, plan, default_time_period, progress)

        print(f"\n{'=' * 60}\nPRE-POPULATION COMPLETE")
        print(f"Entries:            {len(entries)}")
        print(f"Persons created:    {person_stats['created']} (skipped, already done: {person_stats['skipped']})")
        print(f"Plain persons:      {ref_stats['plain_created']} created, {ref_stats['plain_reused']} reused, "
              f"{ref_stats['plain_conflicts']} ambiguous (skipped)")
        print(f"Relationships:      {ref_stats['rels_created']}")
        print(f"Places linked:      {ref_stats['place_rels']}")
        print(f"Tribes linked:      {ref_stats['tribe_rels']}")
        print(f"{'=' * 60}")

    # ─── Plan computation (pure - no DB access) ────────────────────────────────────

    @staticmethod
    def _strip_parenthetical(name: str) -> str:
        """Removes any "(...)" notes from a reference, e.g. "Nahash (textual variant)" -> "Nahash"."""
        return re.sub(r"\s*\(.*?\)\s*", " ", name).strip()

    @classmethod
    def _strip_person_qualifier(cls, name: str) -> Tuple[str, Optional[str]]:
        """
        Splits a person reference into (bare_name, qualifier). Handles, in priority order:
        "X son of Y" / "X daughter of Y" (patronymic/matronymic qualifiers) then the more
        generic "X of Y" (e.g. "Jehoram of Judah"). Parentheticals are stripped first.
        Returns (name, None) if no qualifier pattern is found.
        NOTE: this is only for PERSON references, used to find the matching pre-populated
        entry and to derive a new plain person's display_en_name. It must NOT be applied to
        Place references - place names like "Valley of Salt" or "Tent of Meeting" genuinely
        contain " of " as part of their literal name.
        """
        base = cls._strip_parenthetical(name)
        m = re.match(r"^(.*?)\s+(?:son|daughter)\s+of\s+(.+)$", base, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        m = re.match(r"^(.*?)\s+of\s+(.+)$", base, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return base, None

    @classmethod
    def _entry_names(cls, entry: Dict[str, Any]) -> Set[str]:
        """Lowercase set of every name this entry is known by (name + all_en_names)."""
        names = set(entry.get("all_en_names") or [])
        names.add(entry["name"])
        return {n.lower() for n in names}

    @classmethod
    def _build_name_index(cls, entries: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Maps lowercase name -> list of entry ids known by that name (name or all_en_names)."""
        index: Dict[str, List[str]] = defaultdict(list)
        for entry in entries:
            for name in cls._entry_names(entry):
                if entry["id"] not in index[name]:
                    index[name].append(entry["id"])
        return index

    @classmethod
    def _resolve_person_reference(
        cls, entry: Dict[str, Any], field: str, raw_value: str,
        name_index: Dict[str, List[str]], id_to_entry: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Resolves one raw reference string (e.g. "Joash of Judah", or "Gideon / Jerubbaal")
        from `entry`'s `field` to either: a specific pre-populated entry id ("entry"), a new
        or reused plain person by bare name ("plain"), or nothing ("unresolved" - ambiguous,
        reported for the user to add an explicit refIds entry). See guide §2.5. Returns a
        dict: {"kind": "entry"|"plain"|"unresolved", ...}.
        """
        refids = entry.get("refIds") or {}
        if raw_value in refids:
            return {"kind": "entry", "target_id": refids[raw_value], "method": "refid"}

        alts = cls._split_alt_names(raw_value)
        alt_info = [(alt, *cls._strip_person_qualifier(alt)) for alt in alts]  # (alt, base, qualifier)

        candidates: List[str] = []
        for _, base, _qualifier in alt_info:
            for cand in name_index.get(base.lower(), []):
                if cand not in candidates:
                    candidates.append(cand)

        if not candidates:
            display = alt_info[0][1]
            # Always include the bare display name itself, then every original alt spelling
            # (e.g. "Dodavahu of Mareshah" -> all_names=["Dodavahu", "Dodavahu of Mareshah"]).
            all_names = list(dict.fromkeys([display] + [alt for alt, _, _ in alt_info]))
            return {"kind": "plain", "display": display, "all_names": all_names}

        if len(candidates) == 1:
            return {"kind": "entry", "target_id": candidates[0], "method": "unique"}

        qualifiers = [q for _, _, q in alt_info if q]
        if qualifiers:
            matches = [
                c for c in candidates
                if any(
                    q.lower() in id_to_entry[c].get("description", "").lower() or q.lower() in c.lower()
                    for q in qualifiers
                )
            ]
            if len(matches) == 1:
                return {"kind": "entry", "target_id": matches[0], "method": "qualifier", "candidates": candidates}

        my_names = cls._entry_names(entry)
        reciprocal_matches: List[str] = []
        for cand in candidates:
            for reverse_field in _RECIPROCAL_FIELDS[field]:
                for reverse_raw in id_to_entry[cand].get(reverse_field, []):
                    for reverse_alt in cls._split_alt_names(reverse_raw):
                        reverse_base, _ = cls._strip_person_qualifier(reverse_alt)
                        if reverse_base.lower() in my_names and cand not in reciprocal_matches:
                            reciprocal_matches.append(cand)
        if len(reciprocal_matches) == 1:
            return {"kind": "entry", "target_id": reciprocal_matches[0], "method": "reciprocal", "candidates": candidates}

        return {"kind": "unresolved", "candidates": candidates}

    def _compute_plan(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pure (no DB) computation of the full pre-population plan: resolves every person
        reference in ACTIONABLE_REL_FIELDS, collects place/tribe references, siblings (for
        the report only) and flags issues (bad book names, ignore-filter collisions, dup
        ids). See guide §2.5-§2.7.
        """
        from backend_pipeline.data_pipeline.PydanticModels.EntityIgnoreFilter import is_ignored_entity_name
        from backend.db.data_names.Books import Books

        id_to_entry: Dict[str, Dict[str, Any]] = {}
        dup_ids: List[str] = []
        for entry in entries:
            if entry["id"] in id_to_entry:
                dup_ids.append(entry["id"])
            id_to_entry[entry["id"]] = entry
        name_index = self._build_name_index(entries)

        resolved_entity_refs: List[Dict[str, Any]] = []
        unresolved_refs: List[Dict[str, Any]] = []
        plain_person_refs: Dict[str, Dict[str, Any]] = {}  # display.lower() -> {"display", "all_names", "refs":[...]}
        place_refs: List[Tuple[str, str, str]] = []  # (entry_id, field, raw_value)
        tribe_refs: List[Tuple[str, str]] = []  # (entry_id, raw_value)
        siblings_report: List[Tuple[str, List[str]]] = []
        book_issues: List[str] = []
        ignore_collisions: List[str] = []

        for entry in entries:
            entry_id = entry["id"]

            if is_ignored_entity_name(entry["name"], EntityType.EPerson):
                ignore_collisions.append(
                    f"id='{entry_id}' name='{entry['name']}' -> contains an ignore-filter term; future passage "
                    f"mentions of this name will be dropped before reaching the disambiguator (entity still "
                    f"created, but will be unreachable)."
                )

            for book_name in entry.get("bookReferences", []) or []:
                if Books.get_by_db_name_ignore_case(book_name) is None:
                    book_issues.append(f"id='{entry_id}' bookReferences -> unknown book name '{book_name}'")

            for field in ACTIONABLE_REL_FIELDS:
                for raw_value in entry.get(field, []) or []:
                    result = self._resolve_person_reference(entry, field, raw_value, name_index, id_to_entry)
                    if result["kind"] == "entry":
                        resolved_entity_refs.append({
                            "entry_id": entry_id, "field": field, "raw": raw_value,
                            "target_id": result["target_id"], "method": result["method"],
                        })
                    elif result["kind"] == "plain":
                        key = result["display"].lower()
                        bucket = plain_person_refs.setdefault(key, {
                            "display": result["display"], "all_names": [], "refs": [],
                        })
                        for n in result["all_names"]:
                            if n not in bucket["all_names"]:
                                bucket["all_names"].append(n)
                        bucket["refs"].append((entry_id, field, raw_value))
                    else:
                        unresolved_refs.append({
                            "entry_id": entry_id, "field": field, "raw": raw_value,
                            "candidates": result["candidates"],
                        })

            siblings = entry.get(SIBLINGS_FIELD) or []
            if siblings:
                siblings_report.append((entry_id, siblings))

            for field in _PLACE_FIELDS:
                for raw_value in entry.get(field, []) or []:
                    place_refs.append((entry_id, field, raw_value))

            for raw_value in entry.get(TRIBE_FIELD, []) or []:
                tribe_refs.append((entry_id, raw_value))

        for bucket in plain_person_refs.values():
            if is_ignored_entity_name(bucket["display"], EntityType.EPerson):
                ignore_collisions.append(
                    f"plain person name='{bucket['display']}' (referenced by {bucket['refs']}) -> contains an "
                    f"ignore-filter term; future passage mentions of this name will be dropped before reaching "
                    f"the disambiguator (entity still created, but will be unreachable)."
                )

        return {
            "id_to_entry": id_to_entry,
            "name_index": name_index,
            "dup_ids": dup_ids,
            "resolved_entity_refs": resolved_entity_refs,
            "unresolved_refs": unresolved_refs,
            "plain_person_refs": plain_person_refs,
            "place_refs": place_refs,
            "tribe_refs": tribe_refs,
            "siblings_report": siblings_report,
            "book_issues": book_issues,
            "ignore_collisions": ignore_collisions,
        }

    # ─── Pre-flight check (read-only DB access) ────────────────────────────────────

    def _preflight_check(self, entries: List[Dict[str, Any]], plan: Dict[str, Any], file_path: str) -> List[str]:
        """
        Guide §2.6: pre-population must not run on a graph that already has same-named
        people from another source, since it never merges into them. Any entry id already
        tracked in the progress file (from an earlier, partial run of THIS script) is
        expected to exist and is not an issue. Returns a list of human-readable issues;
        a non-empty list means the caller must stop (see _prepopulate).
        """
        progress = self._load_progress(file_path)
        tracked_keys = set(progress.values())

        issues: List[str] = []
        checked_names: Set[str] = set()
        for entry in entries:
            name = entry["name"]
            if name.lower() in checked_names:
                continue
            checked_names.add(name.lower())

            existing = self.db_api.get_entities_by_display_en_name(name, EntityType.EPerson)
            unexpected = [e for e in existing if e.key not in tracked_keys]
            if unexpected:
                issues.append(
                    f"name='{name}' -> {len(unexpected)} existing EPerson(s) already in the DB that are NOT "
                    f"from a previous run of this script (keys: {[e.key for e in unexpected]}). Pre-population "
                    f"never merges into existing people - clear them or investigate before running."
                )

        if plan["dup_ids"]:
            issues.append(f"Duplicate entry ids in input file: {plan['dup_ids']}")

        return issues

    # ─── Report (guide §2.7) ────────────────────────────────────────────────────────

    def _print_plan_report(self, entries: List[Dict[str, Any]], plan: Dict[str, Any], preflight_issues: List[str]) -> None:
        resolved = plan["resolved_entity_refs"]
        by_method: Dict[str, int] = defaultdict(int)
        for r in resolved:
            by_method[r["method"]] += 1

        print(f"\n{'=' * 60}\nPRE-POPULATION PLAN REPORT\n{'=' * 60}")
        print(f"Entries in file:            {len(entries)}")
        print(f"Person references resolved to a pre-populated entry: {len(resolved)}")
        for method, count in sorted(by_method.items()):
            print(f"    via {method:<10}: {count}")
        print(f"Plain (non-pre-populated) person names referenced:   {len(plan['plain_person_refs'])} "
              f"({sum(len(b['refs']) for b in plan['plain_person_refs'].values())} references)")
        print(f"Unresolved/ambiguous references (NOT linked):        {len(plan['unresolved_refs'])}")
        for u in plan["unresolved_refs"]:
            print(f"    [AMBIGUOUS] id='{u['entry_id']}' field='{u['field']}' raw='{u['raw']}' "
                  f"candidates={u['candidates']} -> add an explicit refIds entry to resolve")
        print(f"Siblings (not stored, listed for review):            "
              f"{sum(len(s) for _, s in plan['siblings_report'])} across {len(plan['siblings_report'])} entries")
        for entry_id, siblings in plan["siblings_report"]:
            print(f"    id='{entry_id}' siblings={siblings}")
        print(f"Place references to link:  {len(plan['place_refs'])}")
        print(f"Tribe references to link:  {len(plan['tribe_refs'])}")

        if plan["book_issues"]:
            print(f"\nInvalid book names ({len(plan['book_issues'])}):")
            for issue in plan["book_issues"]:
                print(f"    [ISSUE] {issue}")

        if plan["ignore_collisions"]:
            print(f"\nIgnore-filter collisions ({len(plan['ignore_collisions'])}) - these entities ARE still "
                  f"created, but future passage mentions of them will never reach the disambiguator:")
            for c in plan["ignore_collisions"]:
                print(f"    [IGNORE-FILTER] {c}")

        if preflight_issues:
            print(f"\n{'=' * 60}\nPRE-FLIGHT ISSUES ({len(preflight_issues)}) - must be resolved before running "
                  f"test_run_prepopulation:\n{'=' * 60}")
            for issue in preflight_issues:
                print(f"    [PRE-FLIGHT] {issue}")
        else:
            print("\nNo pre-flight issues - safe to run test_run_prepopulation.")
        print(f"{'=' * 60}")

    # ─── Progress file (guide §2.6 - idempotency without schema changes) ──────────

    @staticmethod
    def _progress_path(file_path: str) -> str:
        base, _ext = os.path.splitext(file_path)
        return base + ".progress.json"

    @staticmethod
    def _load_progress_file(progress_path: str) -> Dict[str, str]:
        """Returns the entry id -> entity key map, or {} if no progress file exists yet."""
        if not os.path.exists(progress_path):
            return {}
        with open(progress_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_progress(self, file_path: str) -> Dict[str, str]:
        return self._load_progress_file(self._progress_path(file_path))

    @staticmethod
    def _save_progress(file_path: str, progress: Dict[str, str]) -> None:
        """Overwrites the progress file. Called only AFTER a transaction commits (guide §2.6)."""
        progress_path = DBPrePopulateAmbiguosEntitys._progress_path(file_path)
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False, sort_keys=True)

    # ─── Pass 1: one EPerson per entry ──────────────────────────────────────────────

    @staticmethod
    def _build_person_entity(entry: Dict[str, Any], default_time_period: TimePeriod) -> EPerson:
        from backend.db.data_names.Books import Books

        all_en_names = entry.get("all_en_names") or [entry["name"]]
        kwargs: Dict[str, Any] = {
            "display_en_name": entry["name"],
            "entityType": EntityType.EPerson,
            "all_en_names": all_en_names,
            "timePeriod": default_time_period,
            "isWoman": entry.get("isWoman"),      # present value, or None if absent (unknown - NOT False)
            "isNonJew": entry.get("isNonJew"),     # same
            "isGroup": False,
            "roles": [],
        }
        # Only pass through book names the Entity.book_references validator actually accepts -
        # unknown ones are already flagged separately in the plan's book_issues (§2.7) rather
        # than aborting creation of the whole entity.
        valid_books = [b for b in (entry.get("bookReferences") or []) if Books.get_by_db_name_ignore_case(b)]
        if valid_books:
            kwargs["book_references"] = valid_books
        return EPerson.model_validate(kwargs)

    def _run_person_pass(
        self, entries: List[Dict[str, Any]], default_time_period: TimePeriod, progress: Dict[str, str],
        file_path: str,
    ) -> Dict[str, int]:
        """
        Guide §2.6 pass 1: one EPerson per entry, each in its own transaction, progress
        saved after every commit so a re-run skips ids whose key still exists in the DB.
        """
        created = 0
        skipped = 0
        for entry in entries:
            entry_id = entry["id"]
            existing_key = progress.get(entry_id)
            if existing_key and self.db_api.get_entity_by_key(existing_key) is not None:
                skipped += 1
                continue

            person = self._build_person_entity(entry, default_time_period)
            key = self.db_api.run_in_transaction(lambda p=person: self.db_api.insert_entity(p))
            progress[entry_id] = key
            self._save_progress(file_path, progress)
            created += 1
        return {"created": created, "skipped": skipped}

    # ─── Pass 2: resolve references, create plain persons, rels, places, tribes ────

    def _resolve_plain_person_key(
        self, display: str, all_names: List[str], default_time_period: TimePeriod,
    ) -> Optional[str]:
        """
        Guide §2.5 step 4: reuse the one existing EPerson with this exact display name if
        there is exactly one, insert a new bare-name EPerson if there are none, or skip (and
        let the caller report it) if there are several - never guess. Always re-queries the
        DB (no in-process cache) so this stays correct when a transaction is retried.
        """
        existing = self.db_api.get_entities_by_display_en_name(display, EntityType.EPerson)
        if len(existing) == 1:
            return existing[0].key
        if len(existing) > 1:
            return None  # ambiguous among already-created plain/pre-populated persons - don't guess

        person = EPerson.model_validate({
            "display_en_name": display,
            "entityType": EntityType.EPerson,
            "all_en_names": all_names,
            "timePeriod": default_time_period,
            "isGroup": False,
        })
        return self.db_api.insert_entity(person)

    def _insert_symmetric_rel(self, rel_type: RelType, key_a: str, key_b: str) -> None:
        """Inserts rel_type(key_a, key_b) unless it (or its reverse) already exists (guide §2.3)."""
        for rel in self.db_api.get_rels_for_entity(key_a):
            if rel.rel_type == rel_type and {rel.term1, rel.term2} == {key_a, key_b}:
                return
        self.db_api.try_insert_rel(Rel.create(rel_type, key_a, key_b))

    def _run_reference_pass(
        self, entries: List[Dict[str, Any]], plan: Dict[str, Any], default_time_period: TimePeriod,
        progress: Dict[str, str],
    ) -> Dict[str, int]:
        """
        Guide §2.6 pass 2: resolves every actionable reference to a DB key (pre-populated
        entry via `progress`, or a plain person via _resolve_plain_person_key) and creates
        its Rel, plus every associatedWithPlace/diedIn/tribeOfIsrael link. One transaction
        per entry - small, and safe to retry (no non-DB side effects inside the callback).
        """
        stats = {"plain_created": 0, "plain_reused": 0, "plain_conflicts": 0, "rels_created": 0,
                  "place_rels": 0, "tribe_rels": 0}

        id_to_entry = plan["id_to_entry"]
        name_index = plan["name_index"]

        for entry in entries:
            entry_id = entry["id"]
            entry_key = progress.get(entry_id)
            if entry_key is None:
                print(f"  [SKIP] id='{entry_id}' has no entity key (pass 1 must have failed for it) - skipping its refs.")
                continue

            def process_entry(entry=entry, entry_key=entry_key) -> Dict[str, int]:
                local_stats = {"plain_created": 0, "plain_reused": 0, "plain_conflicts": 0, "rels_created": 0,
                               "place_rels": 0, "tribe_rels": 0}

                def resolve_person(field: str, raw_value: str) -> Optional[str]:
                    result = self._resolve_person_reference(entry, field, raw_value, name_index, id_to_entry)
                    if result["kind"] == "entry":
                        return progress.get(result["target_id"])
                    if result["kind"] == "plain":
                        before = self.db_api.get_entities_by_display_en_name(result["display"], EntityType.EPerson)
                        key = self._resolve_plain_person_key(result["display"], result["all_names"], default_time_period)
                        if key is None:
                            local_stats["plain_conflicts"] += 1
                        elif len(before) == 1:
                            local_stats["plain_reused"] += 1
                        else:
                            local_stats["plain_created"] += 1
                        return key
                    return None  # unresolved - already reported in the plan

                for field in ("childOfFather", "childOfMother"):
                    for raw_value in entry.get(field, []) or []:
                        other_key = resolve_person(field, raw_value)
                        if other_key:
                            self.db_api.try_insert_rel(Rel.create(_FIELD_TO_REL_TYPE[field], entry_key, other_key))
                            local_stats["rels_created"] += 1

                for raw_value in entry.get("children", []) or []:
                    child_key = resolve_person("children", raw_value)
                    if child_key:
                        rel_type = RelType.childOfMother if entry.get("isWoman") else RelType.childOfFather
                        self.db_api.try_insert_rel(Rel.create(rel_type, child_key, entry_key))
                        local_stats["rels_created"] += 1

                for raw_value in entry.get("spouseOf", []) or []:
                    spouse_key = resolve_person("spouseOf", raw_value)
                    if spouse_key:
                        self._insert_symmetric_rel(RelType.spouseOf, entry_key, spouse_key)
                        local_stats["rels_created"] += 1

                for field, rel_type in _PLACE_FIELDS.items():
                    for raw_value in entry.get(field, []) or []:
                        alts = self._split_alt_names(raw_value)
                        place = EPlace.create_from_en_name(alts[0], EntityType.EPlace)
                        if len(alts) > 1:
                            place.all_en_names = list(dict.fromkeys(alts))
                        place_key = self.db_api.try_insert_entity(place)
                        self.db_api.try_insert_rel(Rel.create(rel_type, entry_key, place_key))
                        local_stats["place_rels"] += 1

                for raw_value in entry.get(TRIBE_FIELD, []) or []:
                    if raw_value.lower() not in TRIBES_OF_ISRAEL:
                        continue
                    tribe = ETribeOfIsrael.create_from_en_name(raw_value, EntityType.ETribeOfIsrael)
                    tribe_key = self.db_api.try_insert_entity(tribe)
                    self.db_api.try_insert_rel(Rel.create(RelType.personToTribeOfIsrael, entry_key, tribe_key))
                    local_stats["tribe_rels"] += 1

                return local_stats

            entry_stats = self.db_api.run_in_transaction(process_entry)
            for k in stats:
                stats[k] += entry_stats[k]

        return stats

