# Entity search

Source: `frontend/pages/entity_search.py`.

Entity Search has a landing page (`/entity_search`) and one page per entity type (`/entity_search_people`, `_places`, `_nations`, `_tribes`, `_symbols`) - see [urls.md](urls.md). The selected entity is the `id` URL param (set on Go), so a link to `/entity_search_people?id=<key>` opens that entity directly. Every entity page (including the landing page) starts with a "Choose an entity type" button row (People/Places/Nations/Tribes/Symbols, current one highlighted) that calls `navigation.go(<type page>)`, so users need not use the top-menu dropdown. Related-entity "View entity" uses `navigation.go(<type page>, id=...)`; "View sources" goes to Source Search with `rel`/`rel_label` params. Related-entity source search behavior is documented in [Source search](source_search.md). The Symbols selector includes only symbols with at least one relationship.

Source: also rontend/components/entity_filters.py. The people metadata filters (faith, gender, individual/group, roles) and the generic tri-state / multi-checkbox filter helpers live there and are shared: the people tab uses ender_person_filters, and the person selector component (components/person_selector.py, used by both trees - see [trees.md](trees.md)) embeds the same filters.
