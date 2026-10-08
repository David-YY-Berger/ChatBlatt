# Entities & Relationships

Source of truth: `backend/models_db/EntityObjects/*.py`, `backend/models_db/Rel.py`,
`backend/models_db/Enums.py`.

This doc covers what's shared across every entity type (base fields, identity/dedup
philosophy, `Rel`/`RelType`, DB write helpers). **Type-specific fields, identity overrides,
and extraction-time rules live in their own file** — see the index below.

## Per-entity docs

| Entity | Doc |
|---|---|
| `EPerson` | [`entities/person.md`](entities/person.md) |
| `EPlace` | [`entities/place.md`](entities/place.md) |
| `ETribeOfIsrael` | [`entities/tribe_of_israel.md`](entities/tribe_of_israel.md) |
| `ENation` | [`entities/nation.md`](entities/nation.md) |
| `ESymbol` | [`entities/symbol.md`](entities/symbol.md) |
| `ENumber` | [`entities/number.md`](entities/number.md) |
| `EAnimal` | [`entities/animal.md`](entities/animal.md) |
| `EFood` | [`entities/food.md`](entities/food.md) |
| `EPlant` | [`entities/plant.md`](entities/plant.md) |

## Entity (base) — `Entity.py`

| Field | Notes |
|---|---|
| `key` | `str(ObjectId)`, generated on insert |
| `display_en_name` | **always lowercased** by a validator — this is the primary identity field |
| `display_heb_name`, `all_en_names`, `all_heb_names` | `all_en_names` holds every spelling a mention might use (original casing kept) |
| `entityType` | `EntityType` enum |
| `alias_keys` | keys of entities this one is an alias of |
| `book_references` | `Optional[List[str]]`, each a `Book.database_name` (e.g. `"II Kings"`). Validator: case-insensitive → canonical form, dedup, `[]` → `None`, unknown name → `ValueError`. **Only ever set by pre-population** (`control_docs/pipeline/entity_prepopulation.md`) — stays `None` for everything source-derived. |

Transient fields (`TransientField(...)`, `exclude=True`): never stored, filled in for the UI
by `backend/app/controllers/entity_populator.py` from the entity's DB relationships (see
`db_and_collections.md`). Includes `rel_links` (display name → (key, EntityType)) used for
click-through navigation. Every subclass also carries `comparedTo`/`contrastedWith`
(transient) — the only relationship every entity type can participate in.

`to_db_dict()` uses `exclude_none=True, exclude_defaults=True` — a field equal to its
default (e.g. `display_heb_name=""`) is omitted from `$set`, so `update_entity` can never
silently unset/overwrite an already-enriched field with a blank one.

Subclass lookup: `Entity.get_class_for_type(EntityType)`.

## Identity / dedup — "is this the same entity?"

- `get_identity_tuple()` / `build_existence_query()`: default is `(display_en_name, entityType)`.
  Most subclasses use this unmodified — `ENumber` is the one exception, also keying on
  category/unit (see `entities/number.md`). `EPerson` deliberately does **not** override
  these to disambiguate — see `entities/person.md`.
- `has_metadata()`: true once display metadata is filled in. Base check: `display_heb_name`
  set. Subclasses extend it with their own required fields (see each entity's doc). Gates
  whether `DBPopulateEntityEnrichment` sends the entity to the LLM again — an entity with
  full metadata is never re-enriched, so pre-populated entities should eventually get a
  `display_heb_name` too or they stay enrichment-eligible forever (enrichment **can
  overwrite** pre-populated metadata if the entity lacks full metadata — known limitation,
  see `pipeline/entity_prepopulation.md` §open items).

## Rel — `Rel.py`

`key`, `term1` (entity key), `term2` (entity key), `rel_type: RelType`. No direction/meaning
of its own beyond the convention table below.

### RelType directions (`Enums.py`)

| `rel_type` | `term1` → `term2` |
|---|---|
| `childOfFather`, `childOfMother` | child → parent |
| `studiedFrom` | student → teacher |
| `descendantOf` | descendant → ancestor |
| `spouseOf`, `spokeWith`, `disagreedWith`, `enemyOf`, `allyOf`, `comparedTo`, `contrastedWith`, `AliasOf` | **symmetric** — store ONE direction only, never both |
| `bornIn`, `diedIn`, `visited`, `prayedAt` | person → `EPlace` |
| `associatedWithPlace` | person/Symbol → `EPlace`, fallback when no more specific Person→Place type applies |
| `symbolAssociatedWithPlace` | Symbol → `EPlace` |
| `personToTribeOfIsrael` | person → `ETribeOfIsrael` |
| `personBelongsToNation` | person → `ENation` |
| `placeToNation` | place → `ENation` |
| `prophesiedAbout` | person (prophet) → anything |

## DB write helpers — which one to use

| Method | Use for |
|---|---|
| `insert_entity` | Plain insert, no dedup. **Required for Person** (never `try_insert_entity` — would silently merge two different same-named people) |
| `try_insert_entity` | Insert-or-find by `build_existence_query()`. Fine for Place/Tribe/Nation/Symbol/Animal/Food/Plant — never for Person |
| `try_insert_number` | `ENumber`-specific: merges contexts into an existing matching number instead of duplicating |
| `try_insert_rel` | Dedupes on exact `(rel_type, term1, term2)` only — **the reversed pair of a symmetric rel is NOT auto-detected**, check both directions yourself (see `_insert_symmetric_rel` in `DBPrePopulateAmbiguosEntitys.py` for the pattern) |

Full method reference: `data_model/db_and_collections.md`.
