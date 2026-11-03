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
- **Table**: one row per **(unit, source)**, not per context (`_group_by_unit_and_source`).
  Columns: expand chevron, Unit, Source (click opens source popup), Source Summary. The
  chevron pill shows the context count; clicking it expands a panel listing all contexts for
  that unit in that source (rows with no context have no chevron). Rendered as static HTML in
  an iframe; expand/collapse is inline JS that also resizes the iframe (`window.frameElement`).

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
