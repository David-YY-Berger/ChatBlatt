# Trees

Source: `frontend/pages/trees.py`, `frontend/pages/genealogy_tree.py`,
`frontend/pages/studied_from_tree.py`, `frontend/components/tree_graph.py`, and
`frontend/app.py`.

The home page has two separate cards (Genealogy / Studied From) that open each tree directly. Trees has a landing page (`/trees`) and two pages (`/trees_genealogy_tree`, `/trees_studied_from_tree`; see [urls.md](urls.md)). `app.py` passes the page key to `pages/trees.py`, which
dispatches to the genealogy or studied-from page; with no subtab selected it
shows a prompt to pick a tree.

## Genealogy Tree

The implemented tree is a family graph centered on a person:

1. The page renders the shared person selector from
   `frontend/components/person_selector.py`. Person options are loaded from
   the people entity-search handler and cached in Streamlit session state.
   The selector shows the same metadata filters as Entity Search's people tab
   (faith, gender, individual/group, roles — `frontend/components/entity_filters.py`,
   widget keys prefixed per `state_key`) above the combobox; changing a filter
   resets the combobox. The user confirms a person with **Go**; the selected key is retained under
   `genealogy_center_person`.
2. The user chooses depth 1 (direct family) or 2 (family of family). The page
   requests the graph from `GenealogyTreeController` and caches it in session
   state by `(center person key, depth)`.
3. If graph nodes are returned, the page displays the node/edge counts, a
   legend, and the graph embedded as a Pyvis network. With no selected person
   it prompts for one; if the requested person has no matching entity, it
   displays the no-data message.

### Graph data and expansion

`backend/app/controllers/genealogy_tree_controller.py` validates the center
key, clamps requested depth to 1–2, and delegates to
`backend/app/logic/genealogy_tree_logic.py`. The logic returns a
`GenealogyGraphData` DTO (`backend/models_dto/GenealogyGraphData.py`) containing
the center key, person nodes, and relationship edges.

The graph includes database relationships `childOfFather`, `childOfMother`,
and `spouseOf`. Stored parent relationships use the child as `term1` and the
parent as `term2`; spouse relationships are treated as symmetric for
deduplication and display. Sibling edges are synthetic: the logic groups
children by parent and connects children sharing at least one parent. It also
fetches the center person's co-children so siblings are included even at depth
1.

Expansion is breadth-first by relationship hop. Each frontier's family
relationships are fetched in a batch through the MongoDB genealogy mixin, and
unknown endpoint entities are resolved in a batch. Only newly found nodes
are expanded at the next hop. The controller's 1–2 limit is the UI-facing
limit; the logic also has a higher internal depth ceiling as a safeguard for
direct callers.

Each node carries its database key, English display name, center marker, and
optional gender. The renderer uses neutral styling when gender is unknown.
Missing endpoint entities are not rendered as nodes.

### Layout and visual encoding

`_compute_layout` assigns fixed generation rows relative to the center:
parents above, children below, and spouses/siblings on the center's row.
Nodes are positioned in a fixed grid with physics disabled (the shared grid/row layout lives in `components/tree_graph.py`). The center stays
at the horizontal origin; same-generation relatives are placed around it, and
other rows are positioned using related nodes.

Node fill color represents gender (blue for man, rose for woman, gray when
unknown); a gold border ring marks the selected center. Edge styling represents
relationship type: father and mother links have distinct colors, spouse links
are solid, and sibling links are dotted. Relationship labels appear on hover;
the legend summarizes edge and node encodings. The graph is rendered at a
fixed 600px network height inside a 620px Streamlit component.

## Shared rendering (`frontend/components/tree_graph.py`)

Both trees use this module: the generation-row layout (`compute_layout`, which takes
child→parent / parent→child / same-level links and returns positions and levels), gender-based
node fill (blue man, rose woman, gray unknown), the gold selected-person ring, the Pyvis
embedding (`render_pyvis_graph`, edge style supplied by the page) and the legend helpers.
Pages only define their edge parsing, role names, and edge styles.

## Studied From Tree

`frontend/pages/studied_from_tree.py` mirrors the genealogy page: shared person selector
(session key `studied_from_center_person`), a depth radio (1 = direct teachers/students,
2 = teachers/students of those), results cached in session state by `(center key, depth)`,
node/edge counts, legend, and the Pyvis graph.
The page displays a warning that the studied-from data may be corrupted and should not be
relied on, while inviting users to explore it.

Rows: teachers above (`studiedFrom`), the selected person and everyone they `disagreedWith`
on the center row, students below (`taught`, the reverse direction). Node tooltips show the
role (studied from / taught / disagreed with).

Backend: `StudiedFromTreeController.get_studied_from_graph` (clamps depth to 1–2) →
`StudiedFromTreeLogic.build_graph` → `StudiedFromGraphData`
(`backend/models_dto/StudiedFromGraphData.py`: nodes with key, display name, center flag,
optional gender; edges with `from_key`, `to_key`, `rel_type`, label). `studiedFrom` rels are
stored student (`term1`) → teacher (`term2`). The logic runs two independent BFS passes from
the center, one batched query per hop through `get_rels_by_type_for_entities`: upward
(frontier as `term1`, discovering teachers) and downward (frontier as `term2`, discovering
students). `disagreedWith` (symmetric) is fetched for the center only; those people are added
to the center row and are not expanded into their own teachers/students. Edges whose
endpoints don't resolve to entities are dropped; a person found in both directions keeps the
level of the first BFS discovery.

Edge styling: `studiedFrom` is a teal solid arrow from student to teacher; `disagreedWith` is
a red dotted line without arrow.