# EPerson

Source of truth: `backend/models_db/EntityObjects/EPerson.py`.

Individuals **and** groups of people (e.g. Moses, David, Sarah, The 70 Elders, Children of
Israel, The Sanhedrin), plus non-human beings like Angels. Talking animals (e.g. Balaam's
Donkey) are `EAnimal`, not `EPerson`.

## Fields

| Field | Notes |
|---|---|
| `timePeriod` | `Tanach` / `Tanaim` / `Amoraim` / `NoTimePeriod` |
| `isWoman`, `isNonJew`, `isGroup` | `isGroup=True` for collectives like "the 70 elders" |
| `roles` | `List[RoleType]` |

`has_metadata()`: true once the base metadata (`display_heb_name`) **and** `timePeriod`,
`isWoman`, `isNonJew`, `isGroup`, `roles` are all set — gates re-enrichment eligibility.
`DBPopulateEntityEnrichment` only *fills* `timePeriod`/`isWoman`/`isNonJew`/`isGroup` when
currently `None` — it never overwrites an already-set value (protects curated
pre-population data, see `pipeline/entity_prepopulation.md`). `roles` only ever grows (union
of existing + newly-matched roles); `display_heb_name` is overwritten whenever the LLM
returns a non-empty value different from the current one.

Transient relationship fields (not persisted, filled in for the UI by the entity populator):
`childOfFather`, `childOfMother`, `children`, `siblings`, `spouseOf`, `descendantOf`,
`studiedFrom`, `spokeWith`, `disagreedWith`, `allyOf`, `enemyOf`, `bornIn`, `diedIn`,
`visited`, `prayedAt`, `associatedWithPlace`, `tribeOfIsrael`, `belongsToNation`,
`prophesiedAbout`, `comparedTo`, `contrastedWith` — see `EPerson.TRANSIENT_DISPLAY_FIELDS`
for the UI's canonical display order. **There is no sibling `RelType`** — `siblings` is
derived in the UI from two people sharing a parent, not stored as a relationship.

## Identity / dedup — the one exception to the normal rule

`get_identity_tuple()` / `build_existence_query()` are **not overridden** to disambiguate —
both are plain `(display_en_name, entityType)`, same as the base `Entity`. This tuple is only
used for per-source bookkeeping in the populator (each source gets its own name → DB-key map,
since the same name can resolve to different DB entities across different sources).

Telling apart two different people who share a name is **not** the Entity layer's job — it's
`PersonDisambiguator`'s (`backend_pipeline/data_pipeline/entity_resolution/`), using what the
source says about the mention (`PersonSourceContext`). See `pipeline/person_disambiguation.md`.

## DB write rule

**Always `insert_entity`, never `try_insert_entity`** — `try_insert_entity`'s dedup-by-name
would silently merge two different same-named people. `DBPopulateEntityRelGraph` routes every
Person mention through `PersonDisambiguator.find_existing_person_key` first; only a genuinely
new person falls through to `insert_entity`.

## Extraction-time filtering

A Person mention whose name contains a generic/non-proper-noun term as a whole word (e.g.
"King Ahaz", "the advisor") is dropped before it ever reaches `PersonDisambiguator` — see
`pipeline/entity_ignore_filter.md`.
