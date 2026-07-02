# bs"d - lehagdil torah velahadir

from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl
from system_common.Constants import PAGE_MAPS, PAGE_GENOLOGY, PAGE_STUDIED_FROM


def render(lang: str, selected: str | None = None) -> None:
    if selected == PAGE_GENOLOGY:
        from pages.map_genealogy import render as render_genealogy
        render_genealogy(lang)
        return

    if selected == PAGE_STUDIED_FROM:
        title = get_text(f"page_titles.{PAGE_STUDIED_FROM}", lang)
        st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
        st.info(get_text("maps_ui.studied_from_coming_soon", lang))
        return

    # Fallback: top-level Maps page (no sub-tab selected)
    title = get_text(f"page_titles.{PAGE_MAPS}", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.info(get_text("maps_ui.select_map_prompt", lang))

