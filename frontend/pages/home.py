# bs"d - lehagdil torah velahadir

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

import navigation
from pages.trees import TREE_OPTIONS

from translations1 import get_text
from system_common.Constants import (
    PAGE_ENTITY_SEARCH,
    PAGE_NUMBER_SEARCH,
    PAGE_SOURCE_SEARCH,
    PAGE_TREES,
)

ICON_DIR = Path(__file__).resolve().parents[1] / "icons" / "optimized"

TOOLS = (
    (PAGE_NUMBER_SEARCH, "number_search_main.jpg", "home_tools.number_search_description"),
    (PAGE_SOURCE_SEARCH, "source_search_main.jpg", "home_tools.source_search_description"),
    (PAGE_ENTITY_SEARCH, "entity_search_main.jpg", "home_tools.entity_search_description"),
    (PAGE_TREES, "family_tree.jpg", "home_tools.trees_description"),
)


def render(lang: str) -> None:
    title = get_text("page_titles.home", lang)
    subtitle = get_text("home_tools.subtitle", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="home-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns([1, 1, 1, 2])
    for column, (page_key, icon_name, description_key) in zip(columns, TOOLS):
        with column:
            # The button is stretched over the whole card (see styles.css), so any click navigates.
            with st.container(border=True, key=f"home_tool_{page_key}"):
                tool_title = get_text(f"nav.{page_key}", lang)
                st.image(ICON_DIR / icon_name, width=180)
                st.markdown(
                    f'<div class="home-tool-title">{tool_title}</div>',
                    unsafe_allow_html=True,
                )
                if page_key == PAGE_TREES:
                    st.markdown(_tree_description(lang), unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'<div class="home-tool-description">{get_text(description_key, lang)}</div>',
                        unsafe_allow_html=True,
                    )
                if st.button(
                    tool_title,
                    key=f"home_tool_btn_{page_key}_{lang}",
                    use_container_width=True,
                ):
                    navigation.go(page_key)

def _tree_description(lang: str) -> str:
    intro = html.escape(get_text("home_tools.trees_description", lang))
    items = "".join(
        "<li><strong>"
        + html.escape(get_text(f"tree_tabs.{page_key}", lang))
        + "</strong> — "
        + html.escape(get_text(f"trees_ui.descriptions.{page_key}", lang))
        + "</li>"
        for page_key, _ in TREE_OPTIONS
    )
    return (
        '<div class="home-tool-description home-tool-description--trees">'
        f"<p>{intro}</p><ul>{items}</ul></div>"
    )
