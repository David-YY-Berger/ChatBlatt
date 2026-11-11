# bs"d - lehagdil torah velahadir

from __future__ import annotations

from pathlib import Path

import streamlit as st

import navigation

from translations1 import get_text
from system_common.Constants import (
    PAGE_ENTITY_SEARCH,
    PAGE_FAMILY_TREE,
    PAGE_NUMBER_SEARCH,
    PAGE_SOURCE_SEARCH,
    PAGE_STUDIED_FROM,
)

ICON_DIR = Path(__file__).resolve().parents[1] / "icons" / "optimized"

TOOLS = (
    (PAGE_NUMBER_SEARCH, "number_search_main.jpg", "home_tools.number_search_description"),
    (PAGE_SOURCE_SEARCH, "source_search_main.jpg", "home_tools.source_search_description"),
    (PAGE_ENTITY_SEARCH, "entity_search_main.jpg", "home_tools.entity_search_description"),
    (PAGE_FAMILY_TREE, "trees.jpg", "home_tools.family_tree_description"),
    (PAGE_STUDIED_FROM, "trees.jpg", "home_tools.studied_from_description"),
)


def render(lang: str) -> None:
    title = get_text("page_titles.home", lang)
    subtitle = get_text("home_tools.subtitle", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="home-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(len(TOOLS))
    for column, (page_key, icon_name, description_key) in zip(columns, TOOLS):
        with column:
            # The button is stretched over the whole card (see styles.css), so any click navigates.
            with st.container(border=True, key=f"home_tool_{page_key}"):
                tool_title = _tool_title(page_key, lang)
                st.image(ICON_DIR / icon_name, width=180)
                st.markdown(
                    f'<div class="home-tool-title">{tool_title}</div>',
                    unsafe_allow_html=True,
                )
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


def _tool_title(page_key: str, lang: str) -> str:
    if page_key in (PAGE_FAMILY_TREE, PAGE_STUDIED_FROM):
        return get_text(f"page_titles.{page_key}", lang)
    return get_text(f"nav.{page_key}", lang)
