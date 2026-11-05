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

## PDF download (UI only)
After a search, `frontend/pages/source_search.py` shows an icon-only download button beside the "Found N sources" message. It calls `build_results_pdf(ans, search_url)` in `frontend/components/pdf_export.py` (reportlab + python-bidi; DejaVu fonts in `frontend/fonts/`). The PDF has a header banner ("Eitz Habina", main picture linking to `Paths.EITZ_HABINA_URL`, download date/time, and an "Open this search online" link - also printed in full under the header - to the exact search URL with all its params, see `frontend/urls.md`), then each source: English/Hebrew title, passage types, summaries, and Hebrew + English content as plain text (same fields the copy-to-clipboard button uses). Hebrew is rendered RTL; the date/time and page number are in the footer.
