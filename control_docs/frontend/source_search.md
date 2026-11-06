# Source search

Source: `frontend/pages/source_search.py`.

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
- **Relationship search** (from Entity Search): each related-entity item in an entity's detail view opens a compact popover with *View entity* and *View sources*. *View entity* navigates in the current tab; *View sources* opens this page in a new tab with `rel` / `rel_label` URL params (applied by `source_search_logic.apply_url_params` into session key `_source_search_rel`), which shows a "Relationship" chip (with Clear) and auto-runs the search with `SourceSearchQuery.rel_ids` set. The rel keys come from `Entity.rel_keys_by_field` (transient: field name -> display name -> `Rel.key`s), filled by `entity_populator.py`; siblings use the shared parent `childOf` rel keys.
- The old Source Type → Category → Book tree, its chips bar, and `source_filters.css` were removed.

## Shareable URL

Params q, pt, ooks, ent, el, el_label (see [urls.md](urls.md)). source_search_logic.apply_url_params() runs before the widgets render (pre-fills the free-text box, passage types, books, entity panels via set_selected_filters / set_selected_entity_option_keys) and the page then runs the search; after any search sync_url_with_search() writes the form back to the URL and the same link is embedded in the PDF (session key _search_url).

The Person entity dropdown labels each person with their roles (e.g. David (???) - king), same as Entity Search.
