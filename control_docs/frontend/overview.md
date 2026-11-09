# Frontend — UI overview

Source of truth: `frontend/` (Streamlit app). For page-specific controls, results,
and data flows, use the feature guides below.

## Feature guides

- [Number search](number_search.md)
- [Source search](source_search.md)
- [Trees](trees.md)
- [Entity search](entity_search.md)
- [URLs, navigation and shareable searches](urls.md)

## Shared layout and navigation

- `frontend/app.py` initializes the language, renders the header and language
  selector, registers the pages, and runs the page selected by `st.navigation`.
  The header (`components/header.py`) links the title and icon to Home and the
  Sefaria banner to the external site.
- On desktop, the top navigation contains Home, About, Number Search and Source
  Search, plus Entity Search and Trees dropdowns. On screens up to 768px, the
  app also displays a grouped mobile Menu popover; Streamlit hides its top
  navigation on narrow screens. Selecting a mobile menu item closes the popover
  and switches to that page, including when it is already selected. The mobile
  controls are buttons rather than links, and the menu's popover key changes on
  selection so Streamlit remounts it closed. Desktop dropdowns are Streamlit's
  native navigation. Page groups, destinations and query parameters are in
  [URLs, navigation and shareable searches](urls.md).
- `frontend/pages/home.py` presents clickable cards for Number Search, Source
  Search, Entity Search and the two trees. Each keyed card contains an invisible
  stretched button (`styles.css`) that calls `navigation.go(page_key)`; the
  tree cards go directly to their respective tree pages. About currently displays
  placeholder text in the selected language.
- Entity Search has a landing page with entity-type cards and separate
  People, Places, Nations, Tribes and Symbols pages. Those detail pages also
  have a type-picker button row. Trees has a landing page with a selection
  prompt and separate Genealogy and Studied From pages.
- `frontend/components/` contains the shared header, layout, filters, person
  selector, graph rendering and source popup. `frontend/assets/styles.css`
  supplies base and responsive styling; `layout.apply_layout` adds theme and
  language-direction styling.
- When Streamlit reports that a script is running (including page navigation),
  a localized loading overlay covers the page and blocks pointer interaction.
  Browsers supporting CSS `interactivity: inert` also prevent keyboard interaction
  with the main content until the run finishes. Streamlit's Stop button remains
  available.
- Entity dropdowns use Streamlit fragments: changing a selection reruns only the
  relevant selector, not the whole page. Entity Search and tree selectors refresh
  their results on **Go**; Source Search runs on **Find Sources**.
- `frontend/translations1/` contains YAML translations (`en.yml`, `he.yml`) and
  helpers. Use `get_text("path.to.key", lang)`, which falls back to English.
  Page titles use `page_titles.*`; menu labels use `nav.*`, `entity_tabs.*`,
  and `tree_tabs.*`. Update both languages when adding UI text.

## Icons

Put source images in `frontend/icons/orig_icons/`, then run `python frontend/scripts/optimize_icons.py`
(needs Pillow). It writes compressed copies to `frontend/icons/optimized/` (skips up-to-date ones,
removes orphans). The app must only load images from `optimized/` (e.g. the top banner in `app.py`).

## Behavior notes

- **RTL**: selecting Hebrew reorients the page right-to-left and reverses tab order;
  switching back to English reorients left-to-right.
- Source filters, entity metadata, graph names, number results, and source HTML/PDF
  use the selected language. Where Hebrew names, units, contexts, or summaries
  are unavailable in the data, the available English value is displayed instead.
  Search selections retain their underlying identifiers when the language changes.
- **Theme**: respects system `prefers-color-scheme` (dark = deep blues, light = clean
  whites/soft grays).

## Run locally

```bash
cd <repo-root>
pip install -r requirements.txt
streamlit run frontend/app.py
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
