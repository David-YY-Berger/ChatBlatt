# bs"d - lehagdil torah velahadir
"""
Number-search page.
"""

from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl


def render(lang: str) -> None:
    title = get_text("page_titles.number_search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    _rtl = is_rtl(lang)

    st.text_input(get_text("number_search_ui.input_label", lang), key="number_search_query")
    if st.button(get_text("number_search_ui.search_button", lang)):
        st.info(get_text("number_search_ui.coming_soon", lang))
