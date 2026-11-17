# bs"d - lehagdil torah velahadir

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

import navigation
from translations1 import get_text
from system_common.Constants import (
    PAGE_TREES,
    PAGE_FAMILY_TREE,
    PAGE_STUDIED_FROM,
    PAGE_PLACES_VISITED,
    PAGE_DESCENDANTS,
)

ICON_DIR = Path(__file__).resolve().parents[1] / "icons" / "optimized"
TREE_OPTIONS = (
    (PAGE_FAMILY_TREE, "family_tree.jpg"),
    (PAGE_STUDIED_FROM, "studied_from.jpg"),
    (PAGE_PLACES_VISITED, "places_visited.jpg"),
    (PAGE_DESCENDANTS, "descendants.jpg"),
)


def render(lang: str, selected: str | None = None) -> None:
    if selected == PAGE_FAMILY_TREE:
        from pages.genealogy_tree import render as render_genealogy
        render_genealogy(lang)
        return

    if selected == PAGE_STUDIED_FROM:
        from pages.studied_from_tree import render as render_studied_from
        render_studied_from(lang)
        return

    if selected == PAGE_PLACES_VISITED:
        from pages.places_visited import render as render_places_visited
        render_places_visited(lang)
        return

    if selected == PAGE_DESCENDANTS:
        from pages.descendants import render as render_descendants
        render_descendants(lang)
        return

    _render_landing(lang)


def _render_landing(lang: str) -> None:
    title = get_text(f"page_titles.{PAGE_TREES}", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="home-subtitle">{get_text("trees_ui.choose_tree", lang)}</div>',
        unsafe_allow_html=True,
    )

    for column, (page_key, icon_name) in zip(st.columns(len(TREE_OPTIONS)), TREE_OPTIONS):
        with column:
            with st.container(border=True, key=f"home_tool_tree_{page_key}"):
                title = get_text(f"tree_tabs.{page_key}", lang)
                st.image(ICON_DIR / icon_name, width=160)
                st.markdown(
                    f'<div class="home-tool-title">{title}</div>',
                    unsafe_allow_html=True,
                )
                description = html.escape(
                    get_text(f"trees_ui.descriptions.{page_key}", lang)
                )
                st.markdown(
                    f'<div class="tree-option-description">{description}</div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    title,
                    key=f"tree_landing_btn_{page_key}_{lang}",
                    use_container_width=True,
                ):
                    navigation.go(page_key)
