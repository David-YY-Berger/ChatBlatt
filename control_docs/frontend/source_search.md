# Source search

Source: `frontend/pages/source_search.py`.

Layout: narrow left column (Passage Type + Source Type filters) and a main column (entity
dropdowns, free-text box + Find Sources button, results).

- **Passage Type** (`components/source_filters.py`): compact checkbox list, one per
  `PassageType`; no All/None buttons or counts.
- **Source Type** (same module): compact checkbox list for Tanach, Talmud Bavli, Mishna,
  Midrash, and Talmud Yerushalmi. Tanach and Talmud Bavli are available; other types are
  disabled, gray, and marked "Coming soon".
- **Entities** (`components/facets/`): one multiselect per entity type.
- Query building lives in `pages/source_search_logic.py` (`collect_search_query`), which
  fills a `SourceSearchQuery` (`src_types`, `passage_types`, `entity_ids`). Backend flow:
  `search/source_search.md`.
- **Relationship search** (from Entity Search): each related-entity item in an entity's detail view opens a compact popover with *View entity* and *View sources*. *View entity* navigates in the current tab; *View sources* opens this page in a new tab with `rel` / `rel_label` URL params (applied by `source_search_logic.apply_url_params` into session key `_source_search_rel`), which shows a "Relationship" chip (with Clear) and auto-runs the search with `SourceSearchQuery.rel_ids` set. The rel keys come from `Entity.rel_keys_by_field` (transient: field name -> display name -> `Rel.key`s), filled by `entity_populator.py`; siblings use the shared parent `childOf` rel keys.

## Shareable URL

Params q, pt, st, ent, rel, and rel_label (see [urls.md](urls.md)).
`source_search_logic.apply_url_params()` runs before the widgets render (pre-fills the free-text
box, passage and source types, entity panels via `set_selected_filters` /
`set_selected_entity_option_keys`) and the page then runs the search; after any search
`sync_url_with_search()` writes the form back to the URL and the same link is embedded in the
PDF (session key `_search_url`).

The Person entity dropdown labels each person with their roles (e.g. David (???) - king), same
as Entity Search.
