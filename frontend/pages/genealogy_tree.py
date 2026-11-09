# bs"d - lehagdil torah velahadir

"""
Genealogy Tree Page

Renders the Pyvis-powered family-tree graph for a selected person.

Layout:
  1. Person selector (shared component)
  2. Depth selector (1 or 2 edge closeness)
  3. Pyvis network graph embedded via st.components.v1.html
"""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from translations1 import get_text
from components.tree_graph import compute_layout, render_edge_legend, render_node_legend, render_pyvis_graph

# -------------------------------------------------------------------
# Edge colour palette (rel_type → hex colour)
# -------------------------------------------------------------------
_EDGE_COLOURS: dict[str, str] = {
    "childOfFather": "#2196F3",   # blue  – father link
    "childOfMother": "#E91E63",   # pink  – mother link
    "spouseOf":      "#4CAF50",   # green – spouse link
    "sibling":       "#FF9800",   # orange – sibling link
}


def render(lang: str) -> None:
    """Entry point called from trees.py."""
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
# Layout + rendering (shared helpers live in components/tree_graph.py)
# ---------------------------------------------------------------------------

def _compute_layout(graph_data):
    """
    Fixed generation rows relative to the centre person:

        grandparents  ->  parents  ->  [siblings ... center ... spouse]  ->  children  -> grandchildren

    Returns:
        positions: dict[node_key] -> (x, y)
        roles:     dict[node_key] -> role string (shown in the node tooltip)
    """
    center_key = graph_data.center_key

    child_to_parents: dict[str, set] = defaultdict(set)
    parent_to_children: dict[str, set] = defaultdict(set)
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
    positions, level = compute_layout(
        center_key, all_keys, child_to_parents, parent_to_children, same_level_links
    )

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


def _edge_style(edge) -> dict:
    """Relationship TYPE is encoded by line style:
    solid + arrow = parent link (father/mother colour), solid = spouse,
    dotted = sibling."""
    is_sibling = edge.rel_type == "sibling"
    is_symmetric = edge.rel_type in ("spouseOf", "sibling")
    return {
        "color": _EDGE_COLOURS.get(edge.rel_type, "#aaaaaa"),
        "arrows": "" if is_symmetric else "to",
        "dashes": [2, 6] if is_sibling else False,
    }


def _render_pyvis_graph(graph_data, lang: str) -> None:
    positions, roles = _compute_layout(graph_data)
    roles = {key: get_text(f"genealogy_ui.role_{role}", lang) for key, role in roles.items()}
    render_pyvis_graph(graph_data, positions, roles, _edge_style, lang)


def _render_legend(lang: str) -> None:
    render_edge_legend([
        (_EDGE_COLOURS["childOfFather"], "solid-arrow", get_text("entity_fields.childOfFather", lang)),
        (_EDGE_COLOURS["childOfMother"], "solid-arrow", get_text("entity_fields.childOfMother", lang)),
        (_EDGE_COLOURS["spouseOf"],      "solid",       get_text("entity_fields.spouseOf", lang)),
        (_EDGE_COLOURS["sibling"],       "dotted",      get_text("entity_fields.siblings", lang)),
    ])
    render_node_legend(lang)

# ---------------------------------------------------------------------------
# Data loading (cached in session state)
# ---------------------------------------------------------------------------

def _load_graph_data(center_key: str, depth: int):
    """Load graph data, caching per (center_key, depth) pair."""
    from backend.app.controllers.genealogy_tree_controller import GenealogyTreeController

    cache_key = f"_genealogy_graph_{center_key}_{depth}"
    if cache_key not in st.session_state:
        controller = GenealogyTreeController()
        st.session_state[cache_key] = controller.get_genealogy_graph(
            center_person_key=center_key,
            depth=depth,
        )
    return st.session_state[cache_key]
