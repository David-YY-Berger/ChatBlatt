# bs"d - lehagdil torah velahadir

from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl
from system_common.Constants import PAGE_TREES, PAGE_GENOLOGY, PAGE_STUDIED_FROM


def render(lang: str, selected: str | None = None) -> None:
    if selected == PAGE_GENOLOGY:
        from pages.genealogy_tree import render as render_genealogy
        render_genealogy(lang)
        return

    if selected == PAGE_STUDIED_FROM:
        from pages.studied_from_tree import render as render_studied_from
        render_studied_from(lang)
        return

    # Fallback: top-level Trees page (no sub-tab selected)
    title = get_text(f"page_titles.{PAGE_TREES}", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.info(get_text("trees_ui.select_tree_prompt", lang))
