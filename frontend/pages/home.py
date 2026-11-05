# bs"d - lehagdil torah velahadir

from __future__ import annotations

from pathlib import Path

import streamlit as st

import navigation

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
    (PAGE_TREES, "trees_main.jpg", "home_tools.trees_description"),
)


def render(lang: str) -> None:
    title = get_text("page_titles.home", lang)
    subtitle = get_text("home_tools.subtitle", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="home-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(4)
    for column, (page_key, icon_name, description_key) in zip(columns, TOOLS):
        with column:
            with st.container(border=True):
                tool_title = get_text(f"nav.{page_key}", lang)
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
                    get_text("home_tools.open_tool", lang),
                    key=f"home_tool_{page_key}_{lang}",
                    use_container_width=True,
                ):
                    navigation.go(page_key)
