# Control Docs — index

Living reference docs for Copilot (and humans) working on this repo. Each file is scoped,
succinct, and kept up to date — prefer editing an existing doc over adding a new one or
piling on bullet points. See `.github/copilot-instructions.md` for the standing rules that
govern how these docs get used and maintained.

## Data model
| Doc | Covers |
|---|---|
| [`data_model/entities_and_relationships.md`](data_model/entities_and_relationships.md) | Entity base schema, transient fields, RelType directions, identity/dedup philosophy, DB write helpers. Indexes the per-entity docs below. |
| [`data_model/entities/person.md`](data_model/entities/person.md) | `EPerson` fields, identity (no disambiguation at the Entity layer), `insert_entity` rule |
| [`data_model/entities/place.md`](data_model/entities/place.md) | `EPlace` fields, extraction-time exact-match filter |
| [`data_model/entities/tribe_of_israel.md`](data_model/entities/tribe_of_israel.md) | `ETribeOfIsrael` fixed 13-tribe list, auto-overlap with Person |
| [`data_model/entities/nation.md`](data_model/entities/nation.md) | `ENation` demonym conversion, generic-word filter |
| [`data_model/entities/symbol.md`](data_model/entities/symbol.md) | `ESymbol` fields, mutual exclusion with Animal/Food/Plant |
| [`data_model/entities/number.md`](data_model/entities/number.md) | `ENumber` fields, identity (value+category+unit), deterministic exclusions (verse-unit, value 0/1) |
| [`data_model/entities/animal.md`](data_model/entities/animal.md) | `EAnimal` fields, `spokeWith`-only relationship |
| [`data_model/entities/food.md`](data_model/entities/food.md) | `EFood` fields, overlap with Animal/Plant |
| [`data_model/entities/plant.md`](data_model/entities/plant.md) | `EPlant` fields, overlap with Food |
| [`data_model/db_and_collections.md`](data_model/db_and_collections.md) | Mongo collections, `DBapiMongoDB` mixins, transactions, key API methods |

## Population pipeline
| Doc | Covers |
|---|---|
| [`pipeline/population_pipeline_overview.md`](pipeline/population_pipeline_overview.md) | Populator scripts, run order, two-phase LLM scaffold, idempotency conventions |
| [`pipeline/entity_prepopulation.md`](pipeline/entity_prepopulation.md) | Pre-populating well-known ambiguous people (`DBPrePopulateAmbiguosEntitys`) |
| [`pipeline/person_disambiguation.md`](pipeline/person_disambiguation.md) | How a same-named Person mention is routed to the right DB entity |
| [`pipeline/entity_ignore_filter.md`](pipeline/entity_ignore_filter.md) | Non-proper-noun filter for extracted Person/Place names |

## Conventions
| Doc | Covers |
|---|---|
| [`conventions/safety_and_testing.md`](conventions/safety_and_testing.md) | There is no separate test DB; how to test DB logic safely anyway |

## Other areas (stubs — expand as work touches them)
| Doc | Covers |
|---|---|
| [`frontend/overview.md`](frontend/overview.md) | Streamlit app structure, translations, RTL |
| [`search/faiss_bm25.md`](search/faiss_bm25.md) | Semantic (FAISS) + lexical (BM25) search indexes |
| [`app/controllers.md`](app/controllers.md) | Backend controllers that serve the frontend |

## Maintenance rule
After *any* code change — including ad hoc fixes made mid-task, not just planned feature
work — check this index for a doc that covers the touched area and update it in place
(fix/restructure existing content rather than appending). This is part of finishing the
change, not an optional follow-up. Only add a new file when nothing existing fits, and list
it here. If a doc grows unfocused, split or re-outline it.
