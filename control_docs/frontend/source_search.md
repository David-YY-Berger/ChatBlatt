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
- **Relationship search** (from Entity Search): each related-entity item in an entity's detail view opens a compact popover with *View entity* and *View sources*. *View sources* calls `source_search_logic.set_relationship_search(rel_keys, label)` (session keys `_source_search_rel`, `_source_search_rel_pending`), switches to this page, which shows a "Relationship" chip (with Clear) and auto-runs the search with `SourceSearchQuery.rel_ids` set. The rel keys come from `Entity.rel_keys_by_field` (transient: field name -> display name -> `Rel.key`s), filled by `entity_populator.py`; siblings use the shared parent `childOf` rel keys.
- The old Source Type → Category → Book tree, its chips bar, and `source_filters.css` were removed.
