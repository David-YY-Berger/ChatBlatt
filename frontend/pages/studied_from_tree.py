# bs"d - lehagdil torah velahadir

"""
Studied From Tree Page

Pyvis graph for a selected person: teachers above (studied from), students
below (taught), and the people they disagreed with on the person's own row.
"""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from translations1 import get_text
from system_common.Constants import PAGE_STUDIED_FROM
from components.tree_graph import compute_layout, render_edge_legend, render_node_legend, render_pyvis_graph

_EDGE_COLOURS: dict[str, str] = {
    "studiedFrom":   "#26A69A",   # teal – student -> teacher
    "disagreedWith": "#EF5350",   # red  – dispute
}


def render(lang: str) -> None:
    """Entry point called from trees.py."""
    st.markdown(
        f'<div class="page-title">{get_text(f"page_titles.{PAGE_STUDIED_FROM}", lang)}</div>',
        unsafe_allow_html=True,
    )
    st.warning(get_text("studied_from_ui.data_quality_warning", lang))

    st.markdown(f"**{get_text('studied_from_ui.select_person_label', lang)}**")

    from components.person_selector import render_person_selector
    center_key = render_person_selector(lang, state_key="studied_from_center_person")

    if not center_key:
        st.info(get_text("studied_from_ui.prompt_select_person", lang))
        return

    st.divider()
    depth_options = {
        get_text("studied_from_ui.depth_1", lang): 1,
        get_text("studied_from_ui.depth_2", lang): 2,
    }
    chosen = st.radio(
        get_text("genealogy_ui.depth_label", lang),
        options=list(depth_options.keys()),
        horizontal=True,
        key="studied_from_depth_radio",
    )
    depth = depth_options[chosen]

    graph_data = _load_graph_data(center_key, depth)
    if not graph_data.nodes:
        st.warning(get_text("studied_from_ui.no_data", lang))
        return

    st.divider()
    st.markdown(
        f"**{get_text('studied_from_ui.graph_title', lang)}** — "
        f"{len(graph_data.nodes)} {get_text('genealogy_ui.nodes_label', lang)}, "
        f"{len(graph_data.edges)} {get_text('genealogy_ui.edges_label', lang)}"
    )

    render_edge_legend([
        (_EDGE_COLOURS["studiedFrom"],   "solid-arrow", get_text("entity_fields.studiedFrom", lang)),
        (_EDGE_COLOURS["disagreedWith"], "dotted",      get_text("entity_fields.disagreedWith", lang)),
    ])
    render_node_legend(lang)

    positions, roles = _compute_layout(graph_data, lang)
    render_pyvis_graph(graph_data, positions, roles, _edge_style, lang)


def _compute_layout(graph_data, lang: str):
    """
    Rows: teachers' teachers -> teachers -> [center + disagreed-with] -> students -> students' students.
    studiedFrom edges run student -> teacher, so the student plays the "child" role.
    """
    center_key = graph_data.center_key
    student_to_teachers: dict[str, set] = defaultdict(set)
    teacher_to_students: dict[str, set] = defaultdict(set)
    same_level_links: dict[str, set] = defaultdict(set)

    for edge in graph_data.edges:
        if edge.rel_type == "studiedFrom":
            student_to_teachers[edge.from_key].add(edge.to_key)
            teacher_to_students[edge.to_key].add(edge.from_key)
        elif edge.rel_type == "disagreedWith":
            same_level_links[edge.from_key].add(edge.to_key)
            same_level_links[edge.to_key].add(edge.from_key)

    all_keys = [n.key for n in graph_data.nodes]
    positions, level = compute_layout(
        center_key, all_keys, student_to_teachers, teacher_to_students, same_level_links
    )

    def role_of(key: str) -> str:
        lvl = level[key]
        if key == center_key:
            return get_text("studied_from_ui.role_center", lang)
        if lvl == 0:
            return get_text("entity_fields.disagreedWith", lang)
        if lvl < 0:
            return get_text("entity_fields.studiedFrom", lang)
        return get_text("entity_fields.taught", lang)

    return positions, {key: role_of(key) for key in all_keys}


def _edge_style(edge) -> dict:
    """studiedFrom: solid arrow student -> teacher; disagreedWith: dotted, no arrow."""
    is_disagreement = edge.rel_type == "disagreedWith"
    return {
        "color": _EDGE_COLOURS.get(edge.rel_type, "#aaaaaa"),
        "arrows": "" if is_disagreement else "to",
        "dashes": [2, 6] if is_disagreement else False,
    }


def _load_graph_data(center_key: str, depth: int):
    """Load graph data, caching per (center_key, depth) pair."""
    from backend.app.controllers.studied_from_tree_controller import StudiedFromTreeController

    cache_key = f"_studied_from_graph_{center_key}_{depth}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = StudiedFromTreeController().get_studied_from_graph(
            center_person_key=center_key,
            depth=depth,
        )
    return st.session_state[cache_key]
