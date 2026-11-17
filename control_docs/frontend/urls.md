# Frontend - URLs, navigation and shareable searches

Source of truth: `system_common/UrlPaths.py` (shared by `frontend/` and `backend/`; file/dir paths stay in
`backend/common/Paths.py`). `frontend/app.py` builds one `st.Page` per entry with `st.navigation(..., position="top")`
(sections "Entity Search" and "Trees" are dropdowns); `frontend/navigation.py` keeps a page registry and
`navigation.go(page_key, **params)` (wraps `st.switch_page(..., query_params=...)`) for in-app jumps.

The desktop top bar uses Streamlit's native navigation and grouped dropdowns. The app's mobile
Menu popover presents the same pages in the same groups; its buttons use `st.switch_page` and
close the popover on selection, even for the current page. Menu navigation does not carry
search query parameters to the destination. See [overview.md](overview.md) for shared layout.

**Streamlit limitation:** `url_path` cannot contain `/`, so nested URLs are flat (`/entity_search_people`, not
`/entity_search/people`). If the UI is ever rebuilt on a framework with real nesting, only `URL_PATHS` needs changing.

| Page | URL path | Page key |
|---|---|---|
| Home | `/` | `home` |
| About | `/about` | `about` |
| MCP connection instructions | `/mcp_setup` | `mcp` |
| Source search | `/source_search` | `source_search` |
| Number search | `/number_search` | `number_search` |
| Entity search (landing) | `/entity_search` | `entity_search` |
| People / Places / Nations / Tribes / Symbols | `/entity_search_people`, `_places`, `_nations`, `_tribes`, `_symbols` | `people`, `places`, `nations`, `tribes`, `symbols` |
| Trees (landing) | `/trees` | `trees` |
| Family tree | `/trees_genealogy_tree` | `family_tree` |
| Studied-from tree | `/trees_studied_from_tree` | `studied_from` |
| Places visited | `/trees_places_visited` | `places_visited` |
| Descendants | `/trees_descendants` | `descendants` |

The Symbols page key and URL path remain defined internally, but the page is
not exposed in Entity Search navigation.
The MCP instructions page is separate from `/mcp`, which is the protocol endpoint.

## Query parameters (a search is fully described by its URL)

All list values are comma-separated. A page opened with params loads them into its form and runs the search
immediately; running a search rewrites the URL (`st.query_params`), so the address bar is always a shareable link.

- **Source search**: `q` (free text), `pt` (`PassageType` names), `st` (available `SourceType` names), `ent` (entity
  select-option keys from the entity panels), `entity_match=all` (require all selected entities;
  omitted for the default any-entity match), `rel` (`Rel` keys, relationship search from Entity Search),
  `rel_label` (chip text for `rel`).
- **Number search**: `type` = `number` | `unit`, `value` = the number/fraction (e.g. `7`, `1/3`) or the unit's English name.
- **Entity search** (on each `entity_search_<type>` page): `id` = the entity key. Cross-links between entities
  use `navigation.go(<type page>, id=<key>)`.
- **Language**: `lang=en` selects English and `lang=he` selects Hebrew. A missing or invalid value defaults
  to English on a new session. The selected language is reflected in the URL and retained across navigation
  and shareable search links.

Home-page tool cards and Entity Search type-picker buttons navigate with
`navigation.go(<page key>)`. The Trees card opens `/trees`, and its illustrated
choice cards navigate to the corresponding tree URLs above. The desktop dropdown
and mobile Menu expose the same landing and detail pages.

`admin=true` disables analytics and `admin=false` re-enables it; the setting is
propagated through navigation and remembered for the browser tab. Relationship
source links also use `via=entity_relationship_sources` to identify their
origin when opened in a new tab. See [metrics.md](metrics.md) for the opt-out,
privacy rules, event schema, and configuration.

Example: `/source_search?q=abraham&pt=Halacha&lang=he`, `/number_search?type=unit&value=Amah&lang=en`.
`UrlPaths.page_url(page_key, params)` builds absolute links (base URL `UrlPaths.BASE_URL`; `Paths.EITZ_HABINA_URL` is an alias).
Not URL-driven: the two tree pages' center person, Places Visited and Descendants selections (session state).