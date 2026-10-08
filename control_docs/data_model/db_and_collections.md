# DB & Collections

Source of truth: `backend/db/Collections.py`, `backend/db/DBapiMongoDB.py`,
`backend/db/mongo_parts/*.py`.

## Collections

| Collection (`CollectionObjs`) | DB name | Contents |
|---|---|---|
| `TN`, `BT`, `JT`, `RM`, `MS` | `Sources` | `SourceContent` passages (EN/HEB), keyed by source key |
| `ENTITIES` | `Graphs` | entity documents (all `EntityType`s, one collection) |
| `RELATIONS` | `Graphs` | `Rel` documents |
| `SRC_METADATA` | `Graphs` | one `SourceMetadata` per processed source |
| `FS` (`faiss_data`) | `Faiss` | FAISS semantic-search index |
| `BM25` (`bm25_data`) | `Faiss` | BM25 lexical index — own GridFS bucket, fully independent of FAISS |

**Source key**: `"{SourceType name}_{Book.database_name}_{chapter}_{section}"`, e.g.
`TN_II Kings_0_12:1-22`, `BT_Bava Batra_0_16b:1-5`. Books: `backend/db/data_names/Books.py`
(79 books, TN + BT only; `database_name` unique case-insensitively —
`Books.get_by_db_name_ignore_case`).

## `DBapiMongoDB` — composition

Singleton (`@singleton`) composed from mixins in `backend/db/mongo_parts/`:

| Mixin | Responsibility |
|---|---|
| `EntityMongoMixin` | insert/find/update entities (see `entities_and_relationships.md`) |
| `RelationshipMongoMixin` | insert/find rels |
| `GenealogyMongoMixin` | `get_family_rels_for_entity(ies)` — childOfFather/childOfMother/spouseOf only, for genealogy-map BFS |
| `SourceContentMongoMixin` | source passages |
| `SourceMetadataMongoMixin` | per-source summary/entity_keys/rel_keys |
| `SimilarityIndexMongoMixin` | FAISS/BM25 GridFS storage |
| `SelectOptionMongoMixin` | dropdown/filter option lists for the UI |

`get_collection(collection)` returns a plain pymongo `Collection`, or a
`_SessionBoundCollection` (auto session-binding wrapper) while a transaction is active.

## Transactions — `run_in_transaction(callback)`

- Runs `callback()` in one MongoDB transaction; every DB op made through this object during
  the call (reads included) joins it. Commits on return, rolls back on exception.
- **On a transient error, pymongo re-runs `callback` from scratch** — it must have no side
  effects outside the DB (no file writes, no mutating a cache that survives a rollback).
  Safe pattern: re-query the DB fresh inside the callback instead of trusting an
  outer-scope cache (see `DBPrePopulateAmbiguosEntitys._resolve_plain_person_key`).
- Nested transactions raise `RuntimeError`.
- Atlas default `transactionLifetimeLimitSeconds` = 60s, not configurable on shared tiers —
  keep each transaction small (one source, one entry, or a small batch).
- **There is no test DB** — see `conventions/safety_and_testing.md` before running anything
  that writes.

## Key API methods

| Method | Behavior |
|---|---|
| `insert_entity` / `try_insert_entity` / `try_insert_number` | see `entities_and_relationships.md` |
| `get_entities_by_display_en_name(name, entity_type=None)` | exact match (case-insensitive) — the only way to find candidate same-named Persons |
| `get_entity_by_key`, `get_entities_by_keys` | |
| `update_entity` | `$set` of `to_db_dict()` — can never unset a field (see entities doc) |
| `try_insert_rel` | see `entities_and_relationships.md` |
| `get_rels_for_entity(key)` / `get_rels_for_entities(keys)` | rels where entity is term1 OR term2 |
| `get_family_rels_for_entity(ies)` | same, filtered to childOfFather/childOfMother/spouseOf only |
| `upsert_source_metadata` / `get_source_metadata_filtered(entity_ids=...)` | |
| `drop_all_entities()` / `drop_all_rels()` | **destructive**, whole collection |

## SourceMetadata (`backend/models_db/SourceClasses/SourceMetadata.py`)

`key` (= source key, also derives `source_type`), `summary_en`/`summary_heb`,
`passage_types: List[PassageType]`, `entity_keys: Set[str]` (every entity the source
mentions), `rel_keys: Set[str]`. Used by `PersonDisambiguator` to know which books/source
types a candidate person is mentioned in (see `pipeline/person_disambiguation.md`).

`PassageType.STORY_TANACH` vs `STORY_SAGES` (`backend/models_db/Enums.py`): a narrative
about Tanach-era people/events is `STORY_TANACH`; a narrative about the Mishnaic/Talmudic
sages themselves is `STORY_SAGES`. A Tanach source (`source_type == TN`) can only ever be
`STORY_TANACH` — `DBPopulateEntityRelGraph._parse_passage_types` enforces this deterministically
(overriding any `STORY_SAGES` the LLM assigns to a TN passage) rather than trusting the LLM's
call on that point; a Talmudic source is free to be either, decided by the LLM from passage
content (see `pipeline/population_pipeline_overview.md`).
