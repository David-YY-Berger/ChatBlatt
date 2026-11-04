# App Controllers (stub)

Source of truth: `backend/app/controllers/`. These sit between the DB layer
(`data_model/db_and_collections.md`) and the frontend (`frontend/overview.md`). Expand this
doc as work actually touches each controller.

## `entity_populator.py`

`BaseEntityPopulator` (abstract): fills an `Entity`'s transient display fields (e.g.
`EPerson.childOfFather`, `.children`, `.spouseOf`) from its DB relationships, resolving
related entity keys to display names for the UI. Each entity type subclass defines
`REL_FIELD_MAP: Dict[(RelType, direction), transient_field_name]` where `direction` is
`AS_TERM1` (entity is the rel's subject) or `AS_TERM2` (entity is the object — a "reverse"
relationship, e.g. `children` is the reverse of `childOfFather`/`childOfMother`). Also
populates `rel_links` (display name → `(key, EntityType)`) and `rel_keys_by_field` (field -> display name -> `Rel.key`s, for "view sources") for click-through navigation.

## `entity_search/`

One search handler per `EntityType` (`person_search_handler.py`, `place_search_handler.py`,
`number_search_handler.py`, `animal_search_handler.py`, `food_search_handler.py`,
`plant_search_handler.py`, `symbol_search_handler.py`, `nation_search_handler.py`,
`tribe_of_israel_search_handler.py`), fronted by `entity_search_controller.py`.

## Other controllers

- `genealogy_tree_controller.py` — family tree, built via BFS over
  `get_family_rels_for_entity(ies)` (childOfFather/childOfMother/spouseOf only — see
  `data_model/db_and_collections.md`).
- `studied_from_tree_controller.py` — `get_studied_from_graph(key, depth)`; clamps depth to
  1–2 and delegates to `logic/studied_from_tree_logic.py` (BFS over `studiedFrom` via
  `get_rels_by_type_for_entities`; see `frontend/trees.md`).
- `number_search_controller.py` — `ENumber` search/lookup.
- `source_search_controller.py` — passage/source search (works with
  `backend/app/SourceSearchHandler.py` / `SourceSearchQuery.py` and the search indexes,
  `search/faiss_bm25.md`).
