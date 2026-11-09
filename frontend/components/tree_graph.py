# bs"d - lehagdil torah velahadir

"""
Shared helpers for the Pyvis-based tree pages (genealogy, studied-from).

Provides:
  - the node colour palette (fill = gender, gold ring = selected person)
  - a generation-row layout (fixed x/y, no physics) driven by "up" links
    (child -> parents) and same-level links
  - the Pyvis rendering / embedding and the node legend
"""

from __future__ import annotations

import os
import tempfile
from collections import defaultdict, deque
from typing import Callable, Dict, Iterable, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

from translations1 import get_text, is_rtl

# Node colour: one meaning per channel.
#   fill   -> GENDER only
#   border -> SELECTED / not-selected (a highlight ring, not a new colour family)
# Generation is conveyed by vertical position (row), never by colour.
FILL_MAN = "#42A5F5"
FILL_WOMAN = "#F06292"
FILL_UNKNOWN = "#9E9E9E"
SELECTED_RING = "#FFD700"
DEFAULT_BORDER = "#3a3a4a"

# All nodes render at the same size; selection is shown via the ring.
NODE_SIZE = 22

# Layout spacing (fixed grid, no physics)
X_SPACING = 160
Y_SPACING = 180


# ---------------------------------------------------------------------------
# Layout computation (generation-based rows, fixed x/y, no physics)
# ---------------------------------------------------------------------------

def compute_layout(
    center_key: str,
    all_keys: List[str],
    child_to_parents: Dict[str, set],
    parent_to_children: Dict[str, set],
    same_level_links: Dict[str, set],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, int]]:
    """
    Assign (x, y) positions and generation levels relative to the centre
    (level 0; negative = above, positive = below).

    Levels propagate through the up/down links (+-1 per generation) and
    same-level links (0). Computed purely from graph topology.

    Returns:
        positions: node_key -> (x, y)
        level:     node_key -> generation level
    """
    level: Dict[str, int] = {center_key: 0}
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
        for peer in same_level_links.get(cur, ()):
            if peer not in level:
                level[peer] = cur_lvl
                queue.append(peer)
    for key in all_keys:
        level.setdefault(key, 0)  # disconnected fallback

    by_level: Dict[int, list] = defaultdict(list)
    for key in all_keys:
        by_level[level[key]].append(key)

    # Level 0: centre fixed at x=0, same-level peers alternating left/right.
    x_pos: Dict[str, float] = {}
    ordered0 = _order_same_level(center_key, by_level.get(0, []), same_level_links)
    _assign_x_centered_on(center_key, ordered0, x_pos)

    # Other levels: average x of already-placed kin.
    for lvl in sorted([l for l in by_level if l < 0], reverse=True):
        _assign_x_from_relation(by_level[lvl], parent_to_children, x_pos)
    for lvl in sorted([l for l in by_level if l > 0]):
        _assign_x_from_relation(by_level[lvl], child_to_parents, x_pos)

    positions = {key: (x_pos.get(key, 0.0), level[key] * Y_SPACING) for key in all_keys}
    return positions, level


def _order_same_level(center_key: str, level_keys: list, same_level_links: dict) -> list:
    """Order the nodes of a single generation row via BFS out from the centre,
    keeping peers adjacent to the centre. Unreachable nodes are appended at
    the end so nothing is ever dropped."""
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
    """Place `center_key` at x=0 and fan its same-level neighbours out
    alternately to the right and left, in discovery order."""
    if center_key not in ordered0:
        for i, key in enumerate(ordered0):
            x_pos[key] = (i - (len(ordered0) - 1) / 2) * X_SPACING
        return

    x_pos[center_key] = 0.0
    neighbours = [key for key in ordered0 if key != center_key]
    for i, key in enumerate(neighbours):
        rank = i // 2 + 1
        side = 1 if i % 2 == 0 else -1
        x_pos[key] = side * rank * X_SPACING


def _assign_x_from_relation(level_keys: list, relation_map: dict, x_pos: dict) -> None:
    """Position every node in `level_keys` at the average x of its already
    positioned relatives (per `relation_map`), then spread out overlaps."""
    desired: dict[str, float] = {}
    for key in level_keys:
        related = [r for r in relation_map.get(key, ()) if r in x_pos]
        desired[key] = sum(x_pos[r] for r in related) / len(related) if related else 0.0

    ordered = sorted(level_keys, key=lambda k: desired[k])
    prev_x = None
    for key in ordered:
        x = desired[key]
        if prev_x is not None and x < prev_x + X_SPACING:
            x = prev_x + X_SPACING
        x_pos[key] = x
        prev_x = x

    if ordered:
        mean_x = sum(x_pos[k] for k in ordered) / len(ordered)
        for key in ordered:
            x_pos[key] -= mean_x


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def gender_fill(is_woman) -> str:
    """Fill colour by gender; None (unknown / not yet enriched) is neutral grey."""
    if is_woman is True:
        return FILL_WOMAN
    if is_woman is False:
        return FILL_MAN
    return FILL_UNKNOWN


def render_pyvis_graph(
    graph_data,
    positions: Dict[str, Tuple[float, float]],
    roles: Dict[str, str],
    edge_style: Callable[[object], dict],
    lang: str,
) -> None:
    """
    Build the Pyvis network and embed it in the page.

    `edge_style(edge)` returns the keyword arguments (color, arrows, dashes)
    for that edge; the hover title is taken from `edge.label`.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        st.error(get_text("source_search_ui.graph_dependency_error", lang))
        return

    net = Network(
        height="600px",
        width="100%",
        directed=True,
        bgcolor="#1e1e2e",
        font_color="#ffffff",
    )
    net.toggle_physics(False)

    for node in graph_data.nodes:
        role = roles.get(node.key, "")
        fill = gender_fill(node.is_woman)
        is_selected = node.is_center
        border = SELECTED_RING if is_selected else DEFAULT_BORDER
        border_width = 4 if is_selected else 2
        x, y = positions.get(node.key, (0.0, 0.0))
        if is_rtl(lang):
            x = -x

        name = (getattr(node, "display_heb_name", "") or node.display_name) if is_rtl(lang) else node.display_name
        tooltip = name
        if role:
            tooltip += f" ({role})"
        if is_selected:
            tooltip += f" — {get_text('genealogy_ui.role_center', lang)}"

        net.add_node(
            node.key,
            label=name,
            shape="dot",
            color={"background": fill, "border": border, "highlight": {"background": fill, "border": border}},
            borderWidth=border_width,
            size=NODE_SIZE,
            font={"size": 13, "color": "#ffffff"},
            title=tooltip,
            x=x,
            y=y,
            fixed={"x": True, "y": True},
            physics=False,
        )

    for edge in graph_data.edges:
        net.add_edge(
            edge.from_key,
            edge.to_key,
            smooth=False,
            title=get_text(f"entity_fields.{edge.rel_type if edge.rel_type != 'sibling' else 'siblings'}", lang),
            **edge_style(edge),
        )

    net.set_options("""
    var options = {
      "physics": { "enabled": false },
      "edges": { "smooth": false },
      "interaction": { "hover": true, "tooltipDelay": 100 }
    }
    """)

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


def render_edge_legend(edge_items: Iterable[Tuple[str, str, str]]) -> None:
    """edge_items: (colour, style, label) with style 'solid-arrow' | 'solid' | 'dotted'."""
    edge_items = list(edge_items)
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


def render_node_legend(lang: str) -> None:
    """Node legend: fill = gender only. Selection is a ring, not a colour."""
    node_items = [
        (FILL_MAN, False, get_text("genealogy_ui.gender_man", lang)),
        (FILL_WOMAN, False, get_text("genealogy_ui.gender_woman", lang)),
        (FILL_UNKNOWN, False, get_text("genealogy_ui.gender_unknown", lang)),
        (FILL_MAN, True, get_text("genealogy_ui.role_center", lang)),
    ]
    cols = st.columns(len(node_items))
    for col, (colour, selected, label) in zip(cols, node_items):
        with col:
            border = f"3px solid {SELECTED_RING}" if selected else f"1px solid {DEFAULT_BORDER}"
            st.markdown(
                f'<span style="display:inline-block;width:14px;height:14px;'
                f'background:{colour};border:{border};border-radius:50%;'
                f'margin-right:6px;vertical-align:middle;"></span>'
                f'<span style="font-size:0.85rem;">{label}</span>',
                unsafe_allow_html=True,
            )
