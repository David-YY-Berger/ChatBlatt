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

# Node colours
_COLOUR_CENTER = "#FFD700"   # gold for center node
_COLOUR_WOMAN  = "#F48FB1"   # soft pink for women
_COLOUR_MAN    = "#90CAF9"   # soft blue for men


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
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=120)

    # Add nodes
    for node in graph_data.nodes:
        if node.is_center:
            colour = _COLOUR_CENTER
            size = 30
            border = "#FF6F00"
        elif node.is_woman:
            colour = _COLOUR_WOMAN
            size = 20
            border = "#C2185B"
        else:
            colour = _COLOUR_MAN
            size = 20
            border = "#1565C0"

        label = node.display_name
        net.add_node(
            node.key,
            label=label,
            color={"background": colour, "border": border},
            size=size,
            font={"size": 13, "color": "#ffffff"},
            title=label,
        )

    # Add edges
    for edge in graph_data.edges:
        colour = _EDGE_COLOURS.get(edge.rel_type, "#aaaaaa")
        is_symmetric = edge.rel_type in ("spouseOf", "sibling")
        net.add_edge(
            edge.from_key,
            edge.to_key,
            label=edge.label,
            color=colour,
            arrows="to" if not is_symmetric else "",
            dashes=(edge.rel_type == "sibling"),
            font={"size": 10, "color": "#dddddd"},
            title=edge.label,
        )

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
    """Render a compact colour legend for edges."""
    legend_items = [
        (_EDGE_COLOURS["childOfFather"], get_text("entity_fields.childOfFather", lang)),
        (_EDGE_COLOURS["childOfMother"], get_text("entity_fields.childOfMother", lang)),
        (_EDGE_COLOURS["spouseOf"],      get_text("entity_fields.spouseOf", lang)),
        (_EDGE_COLOURS["sibling"],       get_text("entity_fields.siblings", lang)),
    ]
    cols = st.columns(len(legend_items))
    for col, (colour, label) in zip(cols, legend_items):
        with col:
            st.markdown(
                f'<span style="display:inline-block;width:14px;height:14px;'
                f'background:{colour};border-radius:3px;margin-right:6px;'
                f'vertical-align:middle;"></span>'
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
