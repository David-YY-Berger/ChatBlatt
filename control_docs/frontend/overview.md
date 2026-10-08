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
