from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl

LOREM_EN = (
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
)

LOREM_HE = (
    "לורם איפסום דולור סיט אמט, קונסקטטור אדיפיסינג אלית. סחטיר בלמורשך לום, מינסף קוואמן גופה."
)


def render(lang: str, selected: str | None = None) -> None:
    # Determine which page title to show
    if selected:
        title_key = f"page_titles.{selected}"
    else:
        title_key = "page_titles.entity_search"

    title = get_text(title_key, lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    rtl = is_rtl(lang)
    lorem = LOREM_HE if rtl else LOREM_EN
    for _ in range(6):
        st.markdown(lorem)
