# Trees

Source: `frontend/pages/trees.py`, `frontend/pages/genealogy_tree.py`, and
`frontend/app.py`.

The Trees navigation item opens a popover with Genealogy Tree and Studied From
Tree subtabs. `app.py` passes the selected page key to `pages/trees.py`, which
dispatches to the genealogy page or displays the selected tree's title and
placeholder message.

## Genealogy Tree

The implemented tree is a family graph centered on a person:

1. The page renders the shared person selector from
   `frontend/components/person_selector.py`. Person options are loaded from
   the people entity-search handler and cached in Streamlit session state.
   The user confirms a person with **Go**; the selected key is retained under
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
Nodes are positioned in a fixed grid with physics disabled. The center stays
at the horizontal origin; same-generation relatives are placed around it, and
other rows are positioned using related nodes.

Node fill color represents gender (blue for man, rose for woman, gray when
unknown); a gold border ring marks the selected center. Edge styling represents
relationship type: father and mother links have distinct colors, spouse links
are solid, and sibling links are dotted. Relationship labels appear on hover;
the legend summarizes edge and node encodings. The graph is rendered at a
fixed 600px network height inside a 620px Streamlit component.

## Studied From Tree

This subtab is present in navigation, but it is not implemented yet.
`frontend/pages/trees.py` currently shows the translated “coming soon” message;
`backend/app/logic/studied_from_tree_logic.py` is only an empty stub. The
genealogy behavior above describes the existing tree and is not a specification
for the future `studiedFrom` graph.
