# Entity search

Source: `frontend/pages/entity_search.py`.

Entity Search has a landing page (`/entity_search`) and one page per entity type (`/entity_search_people`, `_places`, `_nations`, `_tribes`, `_symbols`) - see [urls.md](urls.md). The selected entity is the `id` URL param (set on Go), so a link to `/entity_search_people?id=<key>` opens that entity directly. Related-entity "View entity" uses `navigation.go(<type page>, id=...)`; "View sources" goes to Source Search with `rel`/`rel_label` params. Related-entity source search behavior is documented in [Source search](source_search.md).
