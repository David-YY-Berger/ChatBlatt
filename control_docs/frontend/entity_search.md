# Entity search

Source: `frontend/pages/entity_search.py`.

Entity Search has a landing page (`/entity_search`) showing one clickable image card per entity type (icons `entity_search_*.jpg` in `icons/optimized/`; People reuses `entity_search_main.jpg`; cards reuse the home-card CSS via the `home_tool_entity_<tab>` key prefix) and one page per entity type (`/entity_search_people`, `_places`, `_nations`, `_tribes`, `_symbols`) - see [urls.md](urls.md). The selected entity is the `id` URL param (set on Go), so a link to `/entity_search_people?id=<key>` opens that entity directly. Each entity-type page has a "Choose an entity type" button row (People/Places/Nations/Tribes/Symbols, current one highlighted) that calls `navigation.go(<type page>)`, so users need not use the top-menu dropdown. Related-entity "View entity" uses `navigation.go(<type page>, id=...)`; "View sources" goes to Source Search with `rel`/`rel_label` params. Related-entity source search behavior is documented in [Source search](source_search.md). The Symbols page shows the same data-quality warning dialog as the Studied From tree when opened; it reappears after navigating away and returning. The Symbols selector includes only symbols with at least one relationship.

Source: also rontend/components/entity_filters.py. The people metadata filters (faith, gender, individual/group, roles) and the generic tri-state / multi-checkbox filter helpers live there and are shared: the people tab uses ender_person_filters, and the person selector component (components/person_selector.py, used by both trees - see [trees.md](trees.md)) embeds the same filters.

Person display: people in the selector combobox are labelled with their roles (David (???) - king), via PersonSelectOption.roles_label(). Related persons in an entity's detail view also show roles (david - king), from the transient Entity.rel_roles (related entity key -> role names) filled by entity_populator.py.

The metadata filters, entity combobox, and Go button share a Streamlit fragment.
Changing a filter or selection reruns only that selector; the currently displayed
entity remains unchanged. Go updates the shareable `id` and reruns the page to
load the selected entity.
