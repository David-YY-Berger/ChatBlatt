# bs"d - lehagdil torah velahadir

"""
Genealogy Map Page

Renders the Pyvis-powered family-tree graph for a selected person.

Layout:
  1. Person selector (shared component)
  2. Depth selector (1 or 2 edge closeness)
  3. Pyvis network graph embedded via st.components.v1.html
"""

from __future__ import annotations

import tempfile
import os
from collections import deque, defaultdict

import streamlit as st
import streamlit.components.v1 as components

from translations1 import get_text, is_rtl

# -------------------------------------------------------------------
# Edge colour palette (rel_type → hex colour)
# -------------------------------------------------------------------
_EDGE_COLOURS: dict[str, str] = {
    "childOfFather": "#2196F3",   # blue  – father link
    "childOfMother": "#E91E63",   # pink  – mother link
    "spouseOf":      "#4CAF50",   # green – spouse link
    "sibling":       "#FF9800",   # orange – sibling link
}

# -------------------------------------------------------------------
# Node colour: one meaning per channel.
#   fill    → GENDER only (this is the only thing colour encodes on nodes)
#   border  → SELECTED / not-selected (a highlight ring, not a new colour
#             family). Generation is conveyed by vertical position (row),
#             never by colour — see _compute_layout().
# -------------------------------------------------------------------
_FILL_MAN     = "#42A5F5"   # blue – male
_FILL_WOMAN   = "#F06292"   # rose – female
_SELECTED_RING = "#FFD700"  # gold ring – marks the selected/centre person
_DEFAULT_BORDER = "#3a3a4a"  # subtle border for everyone else

# All nodes render at the same size; selection is shown via the ring
# above, not by making the node bigger.
_NODE_SIZE = 22

# Layout spacing (fixed grid, no physics)
_X_SPACING = 160
_Y_SPACING = 180


def render(lang: str) -> None:
    """Entry point called from maps.py."""
    st.markdown(
        f'<div class="page-title">{get_text("page_titles.genology", lang)}</div>',
        unsafe_allow_html=True,
    )

    # ── 1. Person selector ────────────────────────────────────────────
    st.markdown(f"**{get_text('genealogy_ui.select_person_label', lang)}**")

    from components.person_selector import render_person_selector
    center_key = render_person_selector(lang, state_key="genealogy_center_person")

    if not center_key:
        st.info(get_text("genealogy_ui.prompt_select_person", lang))
        return

    # ── 2. Depth selector ─────────────────────────────────────────────
    st.divider()
    depth_label = get_text("genealogy_ui.depth_label", lang)
    depth_options = {
        get_text("genealogy_ui.depth_1", lang): 1,
        get_text("genealogy_ui.depth_2", lang): 2,
    }
    chosen_depth_label = st.radio(
        depth_label,
        options=list(depth_options.keys()),
        horizontal=True,
        key="genealogy_depth_radio",
    )
    depth = depth_options[chosen_depth_label]

    # ── 3. Build graph data ───────────────────────────────────────────
    graph_data = _load_graph_data(center_key, depth)

    if not graph_data.nodes:
        st.warning(get_text("genealogy_ui.no_data", lang))
        return

    # ── 4. Render Pyvis graph ─────────────────────────────────────────
    st.divider()
    st.markdown(f"**{get_text('genealogy_ui.graph_title', lang)}** — {len(graph_data.nodes)} {get_text('genealogy_ui.nodes_label', lang)}, {len(graph_data.edges)} {get_text('genealogy_ui.edges_label', lang)}")

    _render_legend(lang)
    _render_pyvis_graph(graph_data, lang)


# ---------------------------------------------------------------------------
# Layout computation (generation-based rows, fixed x/y, no physics)
# ---------------------------------------------------------------------------

def _compute_layout(graph_data):
    """
    Assign a (x, y) position and a family "role" to every node so that the
    graph always renders as fixed generation rows:

        grandparents  →  parents  →  [siblings … center … spouse]  →  children  → grandchildren

    Row (y) is derived from a generation "level" relative to the centre
    person (level 0). Levels propagate through childOf* edges (±1 per
    generation) and spouseOf/sibling edges (same level). This is computed
    purely from graph topology, so the same row layout results whether the
    request was depth=1 or depth=2 — extra hops just add more rows/columns.

    Returns:
        positions: dict[node_key] -> (x, y)
        roles:     dict[node_key] -> role string (used for fill colour)
    """
    center_key = graph_data.center_key

    child_to_parents: dict[str, set] = defaultdict(set)   # child -> {parents}
    parent_to_children: dict[str, set] = defaultdict(set)  # parent -> {children}
    same_level_links: dict[str, set] = defaultdict(set)   # spouse/sibling (undirected)
    spouse_links: dict[str, set] = defaultdict(set)

    for edge in graph_data.edges:
        if edge.rel_type in ("childOfFather", "childOfMother"):
            child_to_parents[edge.from_key].add(edge.to_key)
            parent_to_children[edge.to_key].add(edge.from_key)
        elif edge.rel_type == "spouseOf":
            same_level_links[edge.from_key].add(edge.to_key)
            same_level_links[edge.to_key].add(edge.from_key)
            spouse_links[edge.from_key].add(edge.to_key)
            spouse_links[edge.to_key].add(edge.from_key)
        elif edge.rel_type == "sibling":
            same_level_links[edge.from_key].add(edge.to_key)
            same_level_links[edge.to_key].add(edge.from_key)

    all_keys = [n.key for n in graph_data.nodes]

    # ---- 1. Generation levels via BFS from the centre --------------------
    level: dict[str, int] = {center_key: 0}
    queue = deque([center_key])
    while queue:
        cur = queue.popleft()
        cur_lvl = level[cur]
        for parent in child_to_parents.get(cur, ()):
            if parent not in level:
                level[parent] = cur_lvl - 1
                queue.append(parent)
        for child in parent_to_children.get(cur, ()):
            if child not in level:
                level[child] = cur_lvl + 1
                queue.append(child)
        for sibling in same_level_links.get(cur, ()):
            if sibling not in level:
                level[sibling] = cur_lvl
                queue.append(sibling)
    for key in all_keys:
        level.setdefault(key, 0)  # disconnected fallback

    by_level: dict[int, list] = defaultdict(list)
    for key in all_keys:
        by_level[level[key]].append(key)

    # ---- 2. X position for level 0: centre person fixed at x=0, with -----
    # siblings/spouse alternating left/right around it (closest relations,
    # per BFS discovery order, land nearest the centre on either side).
    x_pos: dict[str, float] = {}
    ordered0 = _order_same_level(center_key, by_level.get(0, []), same_level_links)
    _assign_x_centered_on(center_key, ordered0, x_pos)

    # ---- 3. X position for other levels: average of already-placed kin --
    for lvl in sorted([l for l in by_level if l < 0], reverse=True):
        _assign_x_from_relation(by_level[lvl], parent_to_children, x_pos)
    for lvl in sorted([l for l in by_level if l > 0]):
        _assign_x_from_relation(by_level[lvl], child_to_parents, x_pos)

    positions = {key: (x_pos.get(key, 0.0), level[key] * _Y_SPACING) for key in all_keys}

    # ---- 4. Family role relative to centre (drives fill colour) ---------
    roles: dict[str, str] = {}
    for key in all_keys:
        lvl = level[key]
        if key == center_key:
            roles[key] = "center"
        elif lvl == 0 and center_key in spouse_links.get(key, ()):
            roles[key] = "spouse"
        elif lvl == 0:
            roles[key] = "sibling"
        elif lvl == -1:
            roles[key] = "parent"
        elif lvl <= -2:
            roles[key] = "grandparent"
        elif lvl == 1:
            roles[key] = "child"
        else:
            roles[key] = "grandchild"

    return positions, roles


def _order_same_level(center_key: str, level_keys: list, same_level_links: dict) -> list:
    """Order the nodes of a single generation row via BFS out from the centre,
    keeping spouse/siblings adjacent to the centre. Any node in this row that
    isn't reachable through same-level links (shouldn't normally happen) is
    appended at the end so nothing is ever dropped."""
    if center_key not in level_keys:
        return list(level_keys)

    ordered = [center_key]
    visited = {center_key}
    queue = deque([center_key])
    while queue:
        cur = queue.popleft()
        for neighbour in sorted(same_level_links.get(cur, ())):
            if neighbour in level_keys and neighbour not in visited:
                visited.add(neighbour)
                ordered.append(neighbour)
                queue.append(neighbour)

    for key in level_keys:
        if key not in visited:
            ordered.append(key)
    return ordered


def _assign_x_centered_on(center_key: str, ordered0: list, x_pos: dict) -> None:
    """Places `center_key` at x=0 (the selected entity always renders in the
    visual centre of the graph) and fans its same-level neighbours
    (siblings/spouse) out alternately to the right and left, in the order
    they were discovered, so the centre never drifts to one side no matter
    how many siblings/spouses are added."""
    if center_key not in ordered0:
        for i, key in enumerate(ordered0):
            x_pos[key] = (i - (len(ordered0) - 1) / 2) * _X_SPACING
        return

    x_pos[center_key] = 0.0
    neighbours = [key for key in ordered0 if key != center_key]
    for i, key in enumerate(neighbours):
        rank = i // 2 + 1
        side = 1 if i % 2 == 0 else -1
        x_pos[key] = side * rank * _X_SPACING


def _assign_x_from_relation(level_keys: list, relation_map: dict, x_pos: dict) -> None:
    """Position every node in `level_keys` at the average x of its already
    positioned relatives (parents or children, per `relation_map`), then
    spread out any overlapping nodes so none share/cross an x coordinate."""
    desired: dict[str, float] = {}
    for key in level_keys:
        related = [r for r in relation_map.get(key, ()) if r in x_pos]
        desired[key] = sum(x_pos[r] for r in related) / len(related) if related else 0.0

    ordered = sorted(level_keys, key=lambda k: desired[k])
    prev_x = None
    for key in ordered:
        x = desired[key]
        if prev_x is not None and x < prev_x + _X_SPACING:
            x = prev_x + _X_SPACING
        x_pos[key] = x
        prev_x = x

    if ordered:
        mean_x = sum(x_pos[k] for k in ordered) / len(ordered)
        for key in ordered:
            x_pos[key] -= mean_x


# ---------------------------------------------------------------------------
# Graph rendering
# ---------------------------------------------------------------------------

def _render_pyvis_graph(graph_data, lang: str) -> None:
    """Build the Pyvis network and embed it in the page."""
    try:
        from pyvis.network import Network
    except ImportError:
        st.error("pyvis is not installed. Run: pip install pyvis")
        return

    rtl = is_rtl(lang)

    net = Network(
        height="600px",
        width="100%",
        directed=True,
        bgcolor="#1e1e2e",
        font_color="#ffffff",
    )
    # Fixed generation-row layout: no physics simulation, positions are
    # computed once by _compute_layout() and locked in place per node.
    net.toggle_physics(False)

    positions, roles = _compute_layout(graph_data)

    # Add nodes. Fill = gender only; selection is a ring (border), not a
    # different fill colour or a bigger size — see colour palette above.
    for node in graph_data.nodes:
        role = roles.get(node.key, "")
        fill = _FILL_WOMAN if node.is_woman else _FILL_MAN
        is_selected = node.is_center
        border = _SELECTED_RING if is_selected else _DEFAULT_BORDER
        border_width = 4 if is_selected else 2
        x, y = positions.get(node.key, (0.0, 0.0))

        label = node.display_name
        tooltip = label
        if role:
            tooltip += f" ({role})"
        if is_selected:
            tooltip += " — selected"

        net.add_node(
            node.key,
            label=label,
            shape="dot",
            color={"background": fill, "border": border, "highlight": {"background": fill, "border": border}},
            borderWidth=border_width,
            size=_NODE_SIZE,
            font={"size": 13, "color": "#ffffff"},
            title=tooltip,
            x=x,
            y=y,
            fixed={"x": True, "y": True},
            physics=False,
        )

    # Add edges. Relationship TYPE is encoded purely by line style so it
    # reads as one consistent rule, not text clutter:
    #   solid + arrow   → parent → child (childOfFather/childOfMother)
    #   solid, no arrow → spouse
    #   dotted, no arrow→ sibling (same dash pattern for every sibling edge)
    # Father vs mother is encoded by arrow colour (see _EDGE_COLOURS), not
    # text. The actual relationship label only appears in the hover
    # tooltip (title=...), never as permanent on-canvas text.
    for edge in graph_data.edges:
        colour = _EDGE_COLOURS.get(edge.rel_type, "#aaaaaa")
        is_sibling = edge.rel_type == "sibling"
        is_symmetric = edge.rel_type in ("spouseOf", "sibling")
        net.add_edge(
            edge.from_key,
            edge.to_key,
            color=colour,
            arrows="to" if not is_symmetric else "",
            dashes=[2, 6] if is_sibling else False,
            smooth=False,
            title=edge.label,
        )

    # Global options: physics fully disabled (fixed hierarchical rows,
    # not force-directed), edges drawn as straight lines, and hover
    # tooltips enabled so relationship labels show on demand only.
    net.set_options("""
    var options = {
      "physics": { "enabled": false },
      "edges": { "smooth": false },
      "interaction": { "hover": true, "tooltipDelay": 100 }
    }
    """)

    # Write to a temp HTML file and embed
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        tmp_path = f.name

    try:
        net.save_graph(tmp_path)
        with open(tmp_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=620, scrolling=False)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _render_legend(lang: str) -> None:
    """
    Render compact legends for the two things colour/line-style actually
    encode on this graph:
      - edges:  relationship TYPE, via line style (solid+arrow / solid /
                dotted) plus colour (father vs mother arrow colour)
      - nodes:  GENDER only, via fill colour; selection is shown separately
                as a ring, never as a different fill colour or size
    Relationship labels themselves ("Father", "Sibling", ...) only ever
    appear as hover tooltips on the graph, not as permanent legend/canvas
    text duplicating the colour.
    """
    edge_items = [
        (_EDGE_COLOURS["childOfFather"], "solid-arrow", get_text("entity_fields.childOfFather", lang)),
        (_EDGE_COLOURS["childOfMother"], "solid-arrow", get_text("entity_fields.childOfMother", lang)),
        (_EDGE_COLOURS["spouseOf"],      "solid",       get_text("entity_fields.spouseOf", lang)),
        (_EDGE_COLOURS["sibling"],       "dotted",      get_text("entity_fields.siblings", lang)),
    ]
    cols = st.columns(len(edge_items))
    for col, (colour, style, label) in zip(cols, edge_items):
        with col:
            border_style = "dotted" if style == "dotted" else "solid"
            arrow = "&nbsp;&#8594;" if style == "solid-arrow" else ""
            st.markdown(
                f'<span style="display:inline-block;width:20px;border-top:3px {border_style} {colour};'
                f'margin-right:6px;vertical-align:middle;"></span>'
                f'<span style="font-size:0.85rem;color:{colour};">{arrow}</span> '
                f'<span style="font-size:0.85rem;">{label}</span>',
                unsafe_allow_html=True,
            )

    # Node legend: fill = gender only. Selection is a ring, not a colour.
    node_items = [
        (_FILL_MAN, False, get_text("genealogy_ui.gender_man", lang)),
        (_FILL_WOMAN, False, get_text("genealogy_ui.gender_woman", lang)),
        (_FILL_MAN, True, get_text("genealogy_ui.role_center", lang)),
    ]
    cols = st.columns(len(node_items))
    for col, (colour, selected, label) in zip(cols, node_items):
        with col:
            border = f"3px solid {_SELECTED_RING}" if selected else f"1px solid {_DEFAULT_BORDER}"
            st.markdown(
                f'<span style="display:inline-block;width:14px;height:14px;'
                f'background:{colour};border:{border};border-radius:50%;'
                f'margin-right:6px;vertical-align:middle;"></span>'
                f'<span style="font-size:0.85rem;">{label}</span>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Data loading (cached in session state)
# ---------------------------------------------------------------------------

def _load_graph_data(center_key: str, depth: int):
    """Load graph data, caching per (center_key, depth) pair."""
    from backend.app.controllers.map_genealogy_controller import MapGenealogyController

    cache_key = f"_genealogy_graph_{center_key}_{depth}"
    if cache_key not in st.session_state:
        controller = MapGenealogyController()
        st.session_state[cache_key] = controller.get_genealogy_graph(
            center_person_key=center_key,
            depth=depth,
        )
    return st.session_state[cache_key]
