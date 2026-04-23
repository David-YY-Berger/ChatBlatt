# bs"d - lehagdil torah velahadir

from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl

LOREM_EN = (
    "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident."
)

LOREM_HE = (
    "לורם איפסום דולור סיט אמט, קונסקטטור אדיפיסינג אלית. קולורס מונמס קונס אדיפיסינג אלית."
)


def render(lang: str) -> None:
    title = get_text("page_titles.search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    rtl = is_rtl(lang)
    lorem = LOREM_HE if rtl else LOREM_EN
    for _ in range(8):
        st.markdown(lorem)
