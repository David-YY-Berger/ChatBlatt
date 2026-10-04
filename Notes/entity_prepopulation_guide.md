# Entity pre-population — briefing for an LLM

You are starting in a fresh context and will write the **pre-population script**: a script that seeds the
entity graph with well-known people (Tanach now, Talmud sages later) **before** any source is populated, so
that people who share a name (e.g. two kings named Joash) end up as separate entities and later passage
mentions are routed to the right one.

- **Part 1** explains how population works today (facts, with file paths — read the code to confirm details).
- **Part 2** gives the requirements and guidelines for the pre-population script.

## Ground rules (read first)

- **Every populator "test" connects to the PRODUCTION Atlas DB.** `DBParentClass.setUpClass`
  (`backend_pipeline/data_pipeline/DBScriptParentClass.py`) calls `DBFactory.get_prod_db_mongo()`; there is no
  test DB. Never run a populator — or your script — against it without explicit approval from the user.
  Develop and test against mongomock or a throwaway local MongoDB (see §1.9).
- Do not change the DB schema (new entity fields, collections, indexes) or the disambiguation algorithm without
  asking the user first. Several open questions are listed in §2.9 — raise them, don't decide them.
- Environment: Windows / PowerShell, project venv `.venv1\Scripts\python.exe` (Python 3.11, pydantic 2,
  pymongo 4.13). Install test-only packages into a scratch dir, not the venv.

---

## Part 1 — How population works today

### 1.1 Data model (MongoDB)

| Collection (`backend/db/Collections.py`) | Contents |
|---|---|
| `Sources.TN`, `Sources.BT`, … | `SourceContent`: the passages (EN/HEB), keyed by source key |
| `Graphs.entities` | entity documents |
| `Graphs.relations` | relationship (`Rel`) documents |
| `Graphs.src_metadata` | one `SourceMetadata` per processed source |

**Source key**: `{SourceType name}_{Book.database_name}_{chapter}_{section}`, e.g. `TN_II Kings_0_12:1-22`,
`BT_Bava Batra_0_16b:1-5`. Books are defined in `backend/db/data_names/Books.py` (79 books, TN + BT only;
`database_name` is unique, also case-insensitively).

**Entity** (`backend/models_db/EntityObjects/Entity.py`) — persisted fields:

| Field | Notes |
|---|---|
| `key` | `str(ObjectId)`, generated on insert |
| `display_en_name` | **always lowercased** by a validator |
| `display_heb_name`, `all_en_names`, `all_heb_names`, `entityType`, `alias_keys` | |
| `book_references: Optional[List[str]]` | books the entity is known to appear in, as `Book.database_name` (`"Numbers"`, `"II Kings"`, `"Berakhot"`). Validator: case-insensitive → canonical, duplicates removed, `[]` → `None`, unknown name → `ValueError`. **Meant to be set only by pre-population**; `None` for everything else. |

`to_db_dict()` omits `None`/default values, and `update_entity` is a `$set` of it, so an update can never unset
a field. Subclasses (`Entity.get_class_for_type(EntityType)`): `EPerson` (+ `timePeriod`, `isWoman`, `isNonJew`,
`isGroup`, `roles`), `EPlace` (+ `placeType`), `ETribeOfIsrael`, `ENation`, `ESymbol`, `ENumber`, `EAnimal`, `EFood`,
`EPlant`. Enums (`backend/models_db/Enums.py`): `TimePeriod` = Tanach / Tanaim / Amoraim / NoTimePeriod;
`RoleType` = Prophet / King / Judge / Kohen / Tanna / Amora. Fields like `EPerson.childOfFather`, `children`,
`siblings` are *transient*: not stored, filled for the UI from relationships
(`backend/app/controllers/entity_populator.py`).

**Rel** (`backend/models_db/Rel.py`): `key`, `term1` (entity key), `term2` (entity key), `rel_type` (`RelType`).
Direction conventions:

| `rel_type` | `term1` → `term2` |
|---|---|
| `childOfFather`, `childOfMother` | child → parent (the UI's "children" = rels where the entity is `term2`) |
| `spouseOf`, `spokeWith`, `disagreedWith`, `enemyOf`, `allyOf`, `comparedTo`, `contrastedWith`, `AliasOf` | symmetric — store **one** direction only |
| `studiedFrom` | student → teacher |
| `descendantOf` | descendant → ancestor |
| `bornIn`, `diedIn`, `visited`, `prayedAt`, `associatedWithPlace` | person → `EPlace` |
| `personToTribeOfIsrael` | person → `ETribeOfIsrael` |
| `personBelongsToNation` | person → `ENation` |
| `placeToNation` | place → nation |
| `prophesiedAbout` | person → anything |

There is **no sibling relationship type**: the UI derives siblings from shared parents.

**SourceMetadata**: `key`, `source_type`, `summary_en/heb`, `passage_types`, `entity_keys` (every entity the source
mentions), `rel_keys`.

### 1.2 DB API (`backend/db/DBapiMongoDB.py` + `backend/db/mongo_parts/*`)

`DBapiMongoDB` is a singleton composed of mixins. The methods you will need:

| Method | Behaviour |
|---|---|
| `insert_entity(entity) -> key` | plain insert, no dedupe |
| `try_insert_entity(entity) -> key` | returns the key of the first entity with the same `display_en_name` + `entityType`, else inserts. **Never use it for people who may share a name.** |
| `get_entities_by_display_en_name(name, entity_type=None)`, `get_entity_by_key`, `get_entities_by_keys`, `update_entity` | |
| `try_insert_rel(rel) -> key` | dedupes on the exact `(rel_type, term1, term2)` only — the **reversed pair of a symmetric rel is not detected** |
| `get_rels_for_entity(key)`, `get_rels_for_entities(keys)` | rels where the entity is `term1` or `term2` |
| `upsert_source_metadata`, `get_source_metadata_filtered(entity_ids=…)` | |
| `run_in_transaction(callback)` | see §1.6 |
| `drop_all_entities()`, `drop_all_rels()` | destructive |

### 1.3 Pipeline scripts (`backend_pipeline/data_pipeline/populator_scripts/`)

unittest-style classes; the entry points are `test_*` methods.

- `DBPopulateSourceContent` — loads source passages into `Sources.*` (not covered here).
- `DBPopulateLlmBase` — shared two-phase scaffold: phase 1 calls an LLM per source and writes JSON files to
  `_get_output_dir()`; phase 2 reads them and writes to the DB via `_process_json_entries`. Phase 1 currently
  iterates `get_examples_src_contents()` — a hard-coded handful of example source keys, not whole books.
- `DBPopulateEntityRelGraph` — entities, relationships, source metadata (§1.4).
- `DBPopulateEntityEnrichment` — fills entity metadata (§1.7).
- `DBPopulateMergeEntities` — CSV-driven merge of duplicate entities (§1.8).
- `DBPopulateFaissAndBm25` — search indexes (not covered here).

Intended order once pre-population exists: **pre-population → EntityRelGraph → Enrichment → Merge (as needed)**.

### 1.4 `DBPopulateEntityRelGraph`

Phase-1 output, one JSON file per source (file name = source key with `:` → `;`, directory
`Paths.LMM_RESPONSES_OUTPUT_DIR`):

```json
{"res": {"en_summary": "…", "heb_summary": "…", "passage_types": ["STORY"],
         "Entities": {"Person": [{"en_name": "Joash"}, {"en_name": "Jehoahaz"}], "Place": [{"en_name": "Samaria"}],
                      "TribeOfIsrael": [], "Nation": [], "Symbol": [], "Animal": [], "Food": [], "Plant": [],
                      "Number": [{"en_name": "7", "number_category": "Time", "en_unit": "year", "en_context": "…"}]},
         "Rel": {"childOfFather": [{"term1": "Joash", "term2": "Jehoahaz"}]}},
 "key": "TN_II Kings_0_13:10-13"}
```

Extraction title-cases entity names (`smart_title_case`); tribe entities are also added as Person.

Phase 2 (`test_populate_entities_and_rels_from_jsons` → `_process_json_entries`):

- The JSON entries are sorted with `source_entry_sort_key` (book order, then section — not grouped by source type,
  so e.g. Genesis and Berakhot, both book order 1, interleave).
- Sources are processed **one at a time, each in its own transaction**
  (`db_api.run_in_transaction(self._process_source …)`). If one fails, its writes are rolled back and the run stops;
  earlier sources stay committed. Re-running is safe — nothing is duplicated.
- `_process_source`:
  1. **Entities.** Skip empty names, and names matching the ignore list
     (`EntityIgnoreFilter.is_ignored_entity_name`: Person = **substring** match against
     `backend_pipeline/data_pipeline/PydanticModels/entities_to_ignore/Person`; Place = exact match against
     `…/Place`). Each (name, type) is resolved once per source:
     Person → `PersonDisambiguator.find_existing_person_key(entity, PersonSourceContext)`, and `insert_entity` if
     it returns `None`; every other type → `try_insert_entity` (name + type).
  2. **Relationships.** Both terms are resolved through that source's own name → key map; rels touching an ignored
     entity are skipped; `try_insert_rel`.
  3. **SourceMetadata** upsert (`entity_keys` = every key resolved in this source).
- The populator **never modifies existing entity documents** (names, `book_references`, … stay as you wrote them).

### 1.5 `PersonDisambiguator` (`backend_pipeline/data_pipeline/entity_resolution/PersonDisambiguator.py`)

The module docstring is the spec; summary:

- Input: the mention plus its `PersonSourceContext` (`backend/models_db/EntityObjects/EntityIdentity.py`):
  source key, the mention's relationships in this passage (type, direction, other name), and the names of the
  other entities in the passage. A freshly extracted mention has no metadata of its own.
- **Candidates = EPersons with exactly the same `display_en_name`.** `all_en_names` is *not* used to find
  candidates.
- 0 candidates → new entity.
- Candidates the source **contradicts** are dropped: the passage names a father/mother and the candidate's known
  father/mother (from DB rels) has a different name; or the source is Tanach and the candidate has
  `timePeriod` Tanaim/Amoraim or role Tanna/Amora.
- None left → new entity. One left → that one (even without positive evidence). Two or more → `decide_entity`,
  which narrows step by step:
  1. most relationships in common (same type + direction + other entity); ties: more with a Person, then a Place;
  2. most related entities (through any DB rel) that the passage also mentions;
  3. Tanach sources only: candidates **known to appear** in this book;
  4. fallback by prominence: known in this book, mentions in this book, known in this source type, mentions in
     this source type, mentions overall, relationship count; remaining ties → lowest key (earliest created — so
     pre-populated entities win ties).
- "Known to appear in" = `book_references` ∪ books of the sources whose `SourceMetadata` lists the candidate.
  `book_references` are never treated as complete, so a book missing from them is no contradiction.
- Other entities are matched by name: `display_en_name` + `all_en_names`, case-insensitive, leading "the" ignored;
  `"A / B"` = two alternative names; a bare name matches a qualified one (`"Ahaziah"` ~ `"Ahaziah of Judah"`,
  `"Nahash"` ~ `"Nahash (textual variant)"`); two differently-qualified names never match.
- Every non-trivial decision is printed with the prefix `[PersonDisambiguation]`.

**What this means for pre-population:** a pre-populated person is recognized only through its exact
`display_en_name`, its DB relationships (both directions) and the names of the entities on their other side, its
`timePeriod`/`roles`, and its `book_references`. That is exactly the data the pre-population script must supply.

### 1.6 Transactions (`DBapiMongoDB.run_in_transaction(callback)`)

- Runs `callback()` in one MongoDB transaction and returns its result. Every DB operation made through
  `DBapiMongoDB` during the call (from that thread) joins it automatically — `get_collection` returns a
  session-bound collection, so no session needs to be passed around. Reads see the transaction's own uncommitted
  writes.
- Commit when `callback` returns; rollback if it raises. On a transient error pymongo rolls back and **re-runs
  `callback`**, so it must be safe to repeat (no side effects outside the DB, such as appending to a file).
- Nested transactions raise `RuntimeError`. MongoDB aborts transactions running over 60 s
  (`transactionLifetimeLimitSeconds`, not configurable on Atlas shared tiers) — keep each one small.

### 1.7 Enrichment (`DBPopulateEntityEnrichment`)

For each processed source, entities in its `SourceMetadata.entity_keys` that fail `has_metadata()` are sent to an
LLM together with the passage. The result patches `display_heb_name` and, for EPerson, `timePeriod`, `isWoman`,
`isNonJew`, `isGroup` (**overwritten when different**) and `roles` (unioned). `EPerson.has_metadata()` = non-empty
`display_heb_name` and `timePeriod`, `isWoman`, `isNonJew`, `isGroup` all set. Entities never mentioned by a
processed source are never enriched. Consequence: values the pre-population sets can later be overwritten unless
the entity already has full metadata (including `display_heb_name`) — see §2.9.

### 1.8 Merge (`DBPopulateMergeEntities`)

CSV files in `populator_scripts/entitys_to_merge/<type>_to_merge.csv` list names to merge into one entity. A row
where any name matches more than one entity is skipped as ambiguous, so same-named pre-populated people are never
merged by it. Fields are folded generically (lists, including `book_references`, are unioned).

### 1.9 Testing without touching production

- Build a DB object without connecting: `db = DBapiMongoDB()` (no connection string), then set `db.client` and
  `db.dbs[<db_name>]` to a `mongomock` client and its databases.
- mongomock has no sessions or transactions. Either fake them (a client whose `start_session()` returns an object
  with `__enter__`/`__exit__` and `with_transaction(cb)` that calls `cb(self)`; and strip the `session=` keyword on
  mongomock `Collection` methods) or use a real throwaway single-node replica set:
  `mongod --replSet rs0 --dbpath <tmp dir> --port 27999 --bind_ip 127.0.0.1`, then the admin command
  `replSetInitiate`, then `DBapiMongoDB("mongodb://127.0.0.1:27999/?directConnection=true")`. (Only `mongod.exe` is
  needed; it can be extracted from the official MongoDB zip with HTTP range reads, ~25 MB.)
- To run the graph populator without its production `setUp`:
  `p = DBPopulateEntityRelGraph("test_populate_entities_and_rels_from_jsons"); p.db_api = db;`
  `p.person_disambiguator = PersonDisambiguator(db); p._process_json_entries(entries)` with entries shaped like
  `(source_key, json_dict)` as in §1.4.

---

## Part 2 — The pre-population script

### 2.1 Goal

Seed the graph with well-known people, each as its own `EPerson`, carrying enough identifying data (relationships,
`book_references`, `timePeriod`/`roles`) for `PersonDisambiguator` to route later passage mentions to the right
one. Input now: `Notes/common_entity_pre_populate/tanach_characters.json`; a Talmud-sages file will follow, so make
the script take the input file (and its default `timePeriod`) as parameters. Put it next to the other populator
scripts and follow their style (unittest-style class with a `test_*` entry point, `DBParentClass` base).

### 2.2 Input format (current file)

A JSON list of 167 entries with unique `id`s; 57 names are shared by 2–4 entries (e.g. Abijah ×4, Zechariah ×4).

```json
{
  "id": "joash_king_of_judah",
  "name": "Joash",
  "description": "King of Judah",
  "childOfFather": ["Ahaziah of Judah"],
  "childOfMother": ["Zibiah of Beersheba"],
  "children": ["Amaziah"],
  "associatedWithPlace": ["Jerusalem", "Temple"],
  "bookReferences": ["Numbers"]
}
```

Other fields: `isWoman` (only `true` ever appears, 10 entries), `isNonJew` (only `true`, 7), `spouseOf`,
`siblings`, `diedIn`, `tribeOfIsrael`. Relationship values are **free-text names, not ids**, and include
qualifiers (`"Ahaziah of Judah"`), alternatives (`"Chileab / Daniel"`), notes (`"Nahash (textual variant)"`) and
some non-entities (`"30 sons, each ruling a town"`, `"and six other daughters"`). Only one entry has
`bookReferences` so far.

### 2.3 Field mapping

| JSON | DB |
|---|---|
| each entry | one **new** `EPerson` via `insert_entity` — never `try_insert_entity`, which would merge same-named entries |
| `name` | `display_en_name` (see §2.4) and `all_en_names` |
| `id`, `description` | no DB field — keep them only in the local id → key map and the report (§2.6–2.7) |
| `isWoman`, `isNonJew` | same `EPerson` fields; absent → `False` (the file only marks `true` — confirm with the user) |
| — | `isGroup = False`; `timePeriod = TimePeriod.Tanach` for this file (`Tanaim`/`Amoraim` for sages — this is what enables the Tanna/Amora contradiction rule); `roles` only where certain (e.g. "King of Judah" → `King`) |
| `bookReferences` | `book_references`; map variants to `Book.database_name` first (`"1 Kings"` → `"I Kings"`), otherwise the validator raises |
| `childOfFather` / `childOfMother` | `Rel(childOfFather/childOfMother, term1=this, term2=parent)` |
| `children` | `Rel(childOfMother if this entry isWoman else childOfFather, term1=child, term2=this)` |
| `spouseOf` | `Rel(spouseOf, this, spouse)` — once per pair: check both directions before inserting |
| `siblings` | **not stored** (no rel type). Don't infer parents from siblings (half-siblings). List them in the report. |
| `associatedWithPlace`, `diedIn` | `Rel(associatedWithPlace/diedIn, this, place)`; the `EPlace` via `try_insert_entity`, cleaned name (§2.4) |
| `tribeOfIsrael` | `Rel(personToTribeOfIsrael, this, tribe)`; the `ETribeOfIsrael` via `try_insert_entity`; name must be in `TRIBES_OF_ISRAEL` (`backend_pipeline/data_pipeline/PydanticModels/entity_rel_graph/erg_constants.py`) |

Creating a person, for example:

```python
person = EPerson.model_validate({
    "display_en_name": "Joash", "entityType": EntityType.EPerson, "all_en_names": ["Joash", "Jehoash"],
    "timePeriod": TimePeriod.Tanach, "isWoman": False, "isNonJew": False, "isGroup": False,
    "roles": [RoleType.King], "book_references": ["II Kings", "II Chronicles"],
})
key = db_api.insert_entity(person)
db_api.try_insert_rel(Rel.create(RelType.childOfFather, key, father_key))
```

### 2.4 Names — the most important rule

- `display_en_name` must be **exactly what extraction writes as `en_name`** for that person in passages: the bare
  English name as in the source translation (`"Joash"`, not `"Joash, King of Judah"`). Candidates are found only
  by exact `display_en_name`; a person stored as `"joash king of judah"` would never be found and would be useless.
- `"A / B"` names (12 entries, e.g. `"Joash / Jehoash"`, `"Uzziah / Azariah"`): pick one form as `display_en_name`
  and put every form in `all_en_names`. Mentions spelled with the other form will not find this entity (§2.9).
- The same applies to referenced people and places: strip qualifiers and parentheticals for `display_en_name`
  (`"Allon-bacuth (near Bethel)"` → `"Allon-bacuth"`) and keep the original string in `all_en_names`. Places are
  deduplicated everywhere by exact name + type; there is no place disambiguation.
- Skip and report non-entities (`"David's army"`, `"infant son (died)"`, `"Simeon's Canaanite wife"`, …).
- **Ignore-filter collisions.** The populator drops a Person mention whose name *contains* any ignore term, so such
  mentions never reach the disambiguator and pre-populating them achieves nothing. In this file that hits the entry
  `Manasseh` (`"man"`) and references such as `"Amalek"` (`"male"`) and `"King Ahaz"` (`"king"`); other names
  affected in general include Samson, Haman, Naaman. Check every name with `is_ignored_entity_name`, report
  collisions, and ask the user — don't change the filter yourself.

### 2.5 Resolving relationship references (the hard part)

In the current file, of 382 person references (`childOfFather`, `childOfMother`, `spouseOf`, `children`,
`siblings`), **18** match exactly one entry name, **70** match a name shared by several entries, and **294** match
no entry. Resolve each reference string in this order:

1. An explicit entry `id` (recommend to the user that ambiguous references in the JSON use ids).
2. The normalized name (each `"A / B"` alternative, and the name without its qualifier) matches **exactly one**
   entry → link to that entry's entity.
3. It matches **several** entries → use the qualifier against their `description`/`id`
   (`"Ahaziah of Judah"` → `ahaziah_king_of_judah`) only if exactly one fits; otherwise **don't link** — report it.
4. It matches **no** entry → a plain, non-pre-populated Person: if exactly one EPerson with that display name
   exists, reuse it; if none, insert one (bare name as `display_en_name`, original string in `all_en_names`); if
   several, report it and don't guess.

**A wrong link is worse than a missing one**: a wrong father makes the disambiguator contradict or misroute
mentions permanently. Reciprocal statements (A lists child B, B lists father A) must yield a single rel; report
contradictions (e.g. B given two different fathers).

### 2.6 Run order, idempotency, transactions

- Run **before** `DBPopulateEntityRelGraph`, on a graph without source-derived people. Pre-population does not
  merge into existing same-named people; if any exist, stop and ask the user.
- Two passes: (1) one `EPerson` per entry, so references can resolve to keys; (2) referenced entities and rels.
- Idempotency without schema changes: keep a local mapping file (entry `id` → entity key) next to the script, the
  way the merge script tracks progress in its CSV `merged` column. Write it only **after** each transaction
  commits; on a re-run, skip ids whose key still exists in the DB.
- Wrap each unit of work (one entry, or a small batch) in `db_api.run_in_transaction`; stay well under 60 s per
  transaction on Atlas; keep callbacks repeat-safe (§1.6).

### 2.7 Report

Print and/or write a report for the user to review before anything runs against production: entities created,
rels created, references resolved to entries / to plain persons, ambiguous and unresolved references, skipped
siblings and non-entities, ignore-filter collisions, invalid book names.

### 2.8 Verification

- Every entry → exactly one `EPerson`; same-named entries remain separate entities.
- A re-run creates nothing new.
- On a test DB, feed the graph populator a few synthetic source JSONs (e.g. `TN_II Kings_…` mentioning `"Joash"`
  with father `"Jehoahaz"`) and check that `[PersonDisambiguation]` picks the right pre-populated entity — including
  cases decided only by `book_references`.
- Never run against production without the user's approval.

### 2.9 Open decisions — raise these with the user, don't decide them

1. Should `id`/`description` be stored? (Needs a new entity field.)
2. Should candidate lookup also use `all_en_names`, so `"Jehoash"` mentions find the `"joash"` entity?
3. Ignore-filter substring collisions (Manasseh, Samson, Haman, …): switch Person matching to whole words?
4. Enrichment can overwrite pre-populated `isWoman`/`timePeriod`/… values. Pre-populate `display_heb_name` too (so
   `has_metadata()` is true and enrichment skips them), or change enrichment?
5. Does an absent `isWoman`/`isNonJew` mean `False`?
6. May `roles` be derived from `description` (e.g. "King of Judah" → King)?
