# Search — FAISS + BM25 (stub)

Source of truth: `backend/faiss_api/FaissEngine.py`, `backend/bm25_api/BM25Engine.py`,
`backend/similarity_search_api/` (shared `BaseSimilarityEngine`), populated by
`DBPopulateFaissAndBm25` (`pipeline/population_pipeline_overview.md` step 6).

## What each index is for

- **FAISS** — semantic/embedding similarity search over passage text.
- **BM25** — lexical/keyword similarity search, complementing FAISS. Fully independent
  index/GridFS bucket — can be cleared/rebuilt without touching FAISS.

Both are built from the same source: every `TN` + `BT` `SourceContent`'s clean EN and clean
HEB text (`get_clean_en_text()` / `get_clean_heb_text()`), keyed by source key. Two separate
indexes per engine (`LANG_EN`/`LANG_HEB`).

## Populating

`DBPopulateFaissAndBm25.test_populate_faiss_bm25_index`: clears both indexes (both
languages) first — this is a full rebuild, not incremental — then bulk-populates in batches
with periodic checkpointing to Mongo (crash insurance). Storage lives in the `Faiss` DB
(`Collections.FS` / `Collections.BM25` — see `data_model/db_and_collections.md`).

Expand this doc with query-time usage (how the frontend/controllers call these engines) as
that code gets touched.
