# Entity Pre-population

Script: `backend_pipeline/data_pipeline/populator_scripts/DBPrePopulateAmbiguosEntitys.py`.
Input: `backend_pipeline/data_pipeline/common_entity_pre_populate/ambiguous_tanach_characters.json`
(167 Tanach entries; a Talmud-sages file is expected to follow — the script already takes
the input file + default `TimePeriod` as parameters for that).

## Goal

Seed the graph with well-known people who share a name (e.g. 4 different "Abijah"s) as
separate `EPerson`s, each carrying enough identifying data — relationships, `book_references`,
`timePeriod` — for `PersonDisambiguator` (`person_disambiguation.md`) to route later passage
mentions to the right one. Must run *before* `DBPopulateEntityRelGraph` (no source-derived
same-named people yet).

## Input format

JSON list of entries with a unique `id`. Per-entry fields:

| Field | Meaning |
|---|---|
| `name` | → `display_en_name` (also first element of `all_en_names`) |
| `all_en_names` | optional explicit list of every spelling this person is known by (`name` is always first) |
| `description` | human-readable only — never stored on the entity, kept in the report/progress file for readability |
| `isWoman`, `isNonJew` | stored as-is (`True`/`False`/**absent → `None`/unknown, NOT `False`**) |
| `childOfFather`/`childOfMother`/`children`/`spouseOf`/`siblings` | free-text reference strings (not ids) — see resolution below. `siblings` is report-only, never a Rel (no sibling RelType) |
| `associatedWithPlace`/`diedIn` | place references — `try_insert_entity(EPlace)`, "/" splits alternate names, no qualifier-stripping (place names like "Valley of Salt" genuinely contain "of") |
| `tribeOfIsrael` | must be in `TRIBES_OF_ISRAEL` (`erg_constants.py`) |
| `bookReferences` | → `book_references`, only names `Books.get_by_db_name_ignore_case` accepts; invalid ones are reported, not fatal |
| `refIds` | optional `{raw_reference_string: target_entry_id}` — explicit disambiguation for a reference, highest-priority resolution |

Every created `EPerson` always gets `isGroup=False`, `roles=[]` (not derived from
`description` — rejected as too error-prone) and `timePeriod=default_time_period`.

## Reference resolution (the hard part)

A reference like `"Joash of Judah"` or `"Gideon / Jerubbaal"` must resolve to: a specific
pre-populated entry, a shared "plain" (non-ambiguous) person, or nothing. Order, per raw
reference string (all alt-spellings via `"A / B"` tried together as one candidate set):

1. **Explicit `refIds[raw_value]`** → that entry id.
2. **Qualifier-stripped name** (`"X son of Y"` / `"X daughter of Y"` / `"X of Y"` →
   bare `X`) matches **exactly one** entry name/`all_en_names` → that entry.
3. Matches **several** → narrow by the qualifier against their `description`/`id`, if that
   narrows to exactly one.
4. Still several → **reciprocal confirmation**: if exactly one candidate's own data names
   this entry back (e.g. candidate's `children` list names this entry), pick it. (This is an
   addition beyond the original design doc — on the real file it resolved 56 of 59 otherwise-
   ambiguous references automatically; only 2 needed a manual `refIds` entry.)
5. Still several, or zero qualifiers/reciprocal evidence → **unresolved**, reported, no Rel
   created. A wrong link is worse than a missing one.
6. **Zero entry matches at all** → a "plain" person: reused if exactly one `EPerson` with
   that bare display name already exists in the DB, inserted if none, or skipped+reported if
   several (never guessed). Always re-queries the DB live (no in-process cache) so retried
   transactions stay correct.

## Run shape

- **Pass 1**: one `EPerson` per entry (`insert_entity`, never `try_insert_entity` — same-named
  entries must stay separate). One transaction per entry.
- **Pass 2**: resolve every reference (needs pass 1's id→key map complete first) and create
  the corresponding `Rel`s, plus place/tribe links. One transaction per entry.
- **Idempotency**: a `<input>.progress.json` file (next to the input, gitignored-by-convention
  scratch data) maps entry id → DB key, written only after that entry's pass-1 transaction
  commits. Re-running skips any id whose key still resolves in the DB. Plain persons need no
  such file — they're found by a live DB name query every time.
- **Pre-flight guard**: before writing anything, every entry name is checked against the DB;
  any existing same-named `EPerson` not accounted for by the progress file aborts the whole
  run (pre-population never merges into existing people).

## Entry points

- `test_print_prepopulation_report` — **read-only**, safe anytime: loads the file, computes
  the full resolution plan, prints it (resolved/unresolved counts, plain persons, siblings,
  ignore-filter collisions, bad book names) plus the pre-flight check. Always run this first.
- `test_run_prepopulation` — does the real writes for the Tanach file (`TimePeriod.Tanach`).

## Known limitations (by design, not bugs)

- `all_en_names` matching is NOT used to find Person candidates elsewhere in the pipeline —
  only exact `display_en_name` (see `person_disambiguation.md`). A mention spelled with an
  alternate form (e.g. "Jehoash" when the entity is stored as "Joash") won't be found.
- Two different, never-pre-populated people who happen to share a bare name (e.g. two
  unrelated minor "Zabad"s) get silently treated as one plain person — no evidence exists to
  tell them apart at pre-population time.
- Entities whose name collides with the ignore filter (see `entity_ignore_filter.md`) are
  still created but unreachable from future source mentions — reported, not blocking.
- A pre-populated entity never gets a `display_heb_name` (no Hebrew names in this input file
  yet), so it stays enrichment-eligible forever (`has_metadata()` never true) — that's
  intended, it's how `display_heb_name` eventually gets filled in from a source mention.
  `DBPopulateEntityEnrichment` only *fills* `timePeriod`/`isWoman`/`isNonJew`/`isGroup` when
  still unset; it never overwrites an already-curated value, so repeated enrichment passes
  can't clobber this file's data.
