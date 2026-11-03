# Frontend — Overview (stub)

Source of truth: `frontend/` (Streamlit app). Expand this doc as work actually touches the
frontend — it's currently a light pointer, not a full reference.

## Structure

- `frontend/app.py` — entry point; language toggle + custom nav buttons. Entity Search and
  Maps use a popover dropdown for subtabs.
- `frontend/translations1/` — YAML translations (`en.yml`, `he.yml`) + helpers. Use
  `get_text("path.to.key", lang)`; falls back to English if a key is missing. Page titles
  under `page_titles.*`, nav labels under `nav.*`/`entity_tabs.*`/`map_tabs.*`.
- `frontend/components/` — shared UI pieces (`header.py`, `layout.py`).
- `frontend/pages/` — tab renderers.
- `frontend/assets/styles.css` — base styling; RTL/dark/light tweaks in `layout.apply_layout`.

## Number search page (`frontend/pages/number_search.py`)

Flow: `NumberSearchController` → `NumberSearchLogic.execute` (backend) returns
`NumberSearchResult.by_category` (`NumberCategory | None` → list of `NumberOccurrenceDTO`, one
per context × source). Entity model: `data_model/entities/number.md`.

- **Input**: one free-form box (Enter or Search button). Whole vs. fraction auto-detected;
  `_validate_number` gives live error messages (rejects 0/1, decimals, negatives).
- **Results**: big number header → coloured category tabs (with counts) → per-tab unit filter
  → table.
- **Results list**: organised by **unit** (`_group_by_unit`). Every unit is a collapsed card showing a chevron, the unit name and a source-count badge. Opening a card reveals one row per source: Context(s) (all contexts of that unit in that source, merged), Source Summary, and Source (click opens the source popup, positioned near the click ? see `components/source_popup.py` `spOpen`). Rendered as static HTML in an iframe; expand/collapse is inline JS that also resizes the iframe (`window.frameElement`).

## Source search page (`frontend/pages/source_search.py`)

Layout: narrow left column (Passage Type + Books filters) and a main column (entity
dropdowns, free-text box + Find Sources button, results).

- **Passage Type** (`components/source_filters.py`): compact checkbox list, one per
  `PassageType`; no All/None buttons or counts.
- **Books** (same module): multiselect of every `Books.sorted_all()` book (English display name),
  same behavior as the entity multiselects. Resolved to `Book.database_name` values.
- **Entities** (`components/facets/`): one multiselect per entity type.
- Query building lives in `pages/source_search_logic.py` (`collect_search_query`), which
  fills a `SourceSearchQuery` (`passage_types`, `book_names`, `entity_ids`). Backend flow:
  `search/source_search.md`.
- The old Source Type → Category → Book tree, its chips bar, and `source_filters.css` were removed.
## Behavior notes

- **RTL**: selecting Hebrew reorients the page right-to-left and reverses tab order;
  switching back to English reorients left-to-right.
- **Theme**: respects system `prefers-color-scheme` (dark = deep blues, light = clean
  whites/soft grays).

## Run locally

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Backend data the frontend reads/searches comes from `backend/app/controllers/`
(`app/controllers.md`) and the search indexes (`search/faiss_bm25.md`).

## requirements.txt is the deployment manifest

`requirements.txt` (repo root) is what Streamlit Community Cloud installs — it must only
list packages actually imported by `frontend/` + `backend/`, and must pip-resolve cleanly
(no conflicting pins). `backend/models_db` and `backend/models_dto` use `pydantic`, so it
stays in this file; `pydantic-ai` (and the rest of the LLM pipeline stack) is only imported
by `backend_pipeline/` (local data-population scripts), so it does **not** belong here.

`requirements_ignore_old.txt` is a full `pip freeze` record of the local dev environment
(pipeline + app deps together) — kept for reference, never installed by the deployed app.
When bumping a shared pin (e.g. `pydantic`) in `requirements.txt`, re-check it against what
that file shows worked locally (e.g. the `typing_extensions` floor pydantic now requires).
