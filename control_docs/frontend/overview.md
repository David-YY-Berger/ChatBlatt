# Frontend — Overview (stub)

Source of truth: `frontend/` (Streamlit app). Expand these docs as work actually
touches the frontend; they are currently light pointers, not a full reference.

## Feature guides

- [Number search](number_search.md)
- [Source search](source_search.md)
- [Trees](trees.md)
- [Entity search](entity_search.md)
- [URLs, navigation and shareable searches](urls.md)

## Structure

- `frontend/app.py` — entry point; language selector + `st.navigation` (top) with one URL per page (see [urls.md](urls.md)).
- `frontend/translations1/` — YAML translations (`en.yml`, `he.yml`) + helpers. Use
  `get_text("path.to.key", lang)`; falls back to English if a key is missing. Page titles
  under `page_titles.*`, nav labels under `nav.*`/`entity_tabs.*`/`tree_tabs.*`.
- `frontend/components/` — shared UI pieces (`header.py`, `layout.py`).
- `frontend/pages/` — tab renderers.
- `frontend/assets/styles.css` — base styling; RTL/dark/light tweaks in `layout.apply_layout`.

## Icons

Put source images in `frontend/icons/orig_icons/`, then run `python frontend/scripts/optimize_icons.py`
(needs Pillow). It writes compressed copies to `frontend/icons/optimized/` (skips up-to-date ones,
removes orphans). The app must only load images from `optimized/` (e.g. the top banner in `app.py`).

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
list packages actually imported by `frontend/` + `backend/`, and it must pip-resolve cleanly
(no conflicting pins). `backend/models_db` and `backend/models_dto` use `pydantic`, so it
stays in this file; `pydantic-ai` (and the rest of the LLM pipeline stack) is only imported
by `backend_pipeline/` (local data-population scripts), so it does **not** belong here.

`requirements_ignore_old.txt` is a full `pip freeze` record of the local dev environment
(pipeline + app deps together) — kept for reference, never installed by the deployed app.
When bumping a shared pin (e.g. `pydantic`) in `requirements.txt`, re-check it against what
that file shows worked locally (e.g. the `typing_extensions` floor pydantic now requires).
