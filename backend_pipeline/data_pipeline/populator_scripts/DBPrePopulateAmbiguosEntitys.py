# bs"d
import json
from typing import Any, Dict, List, Optional

from backend.common import Paths
from backend.db.Collections import CollectionObjs
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass

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
