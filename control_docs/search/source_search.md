# Search — Source search flow

Source of truth: `backend/app/SourceSearchHandler.py`, `backend/app/SourceSearchQuery.py`,
`backend/db/mongo_parts/source_metadata_mixin.py` (`get_source_metadata_filtered`).

`SourceSearchQuery` fields: `free_text_similarity`, `max_sources`, `passage_types`,
`book_names` (`Book.database_name` values), `entity_ids`, `rel_ids`. (`src_types` exists but is
not currently applied by the backend.)

1. **Structural filter** — one Mongo query on `SRC_METADATA`. Within a dimension values are
   OR'd (`$in`); dimensions are AND'd; an empty dimension is not filtered.
   - `passage_types` → `passage_types` array.
   - `book_names` → regex on `key`: `^[A-Z]{2}_(book1|book2)_` (names are `re.escape`d; the
     book is the 2nd `_`-segment of the source key, see `data_model/db_and_collections.md`).
   - `entity_ids` / `rel_ids` → `entity_keys` / `rel_keys` arrays.
2. **Re-rank** (only if free text given) — FAISS + BM25 fused by RRF; reorders only, never filters
   (`search/faiss_bm25.md`).
3. Truncate to `max_sources`, then load `SourceContent` for each.
UI entry point for `rel_ids`: Entity Search 'View sources' (see `frontend/overview.md`) passes the Rel keys behind a relationship list item.
