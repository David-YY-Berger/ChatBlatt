# Control Docs — index

Living reference docs for Copilot (and humans) working on this repo. Each file is scoped,
succinct, and kept up to date — prefer editing an existing doc over adding a new one or
piling on bullet points. See `.github/copilot-instructions.md` for the standing rules that
govern how these docs get used and maintained.

## Data model
| Doc | Covers |
|---|---|
| [`data_model/entities_and_relationships.md`](data_model/entities_and_relationships.md) | Entity/EPerson/EPlace/... schema, transient fields, RelType directions, identity/dedup rules |
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
After a code change, check this index for a doc that covers the touched area and update it
in place (fix/restructure existing content rather than appending). Only add a new file when
nothing existing fits, and list it here. If a doc grows unfocused, split or re-outline it.
