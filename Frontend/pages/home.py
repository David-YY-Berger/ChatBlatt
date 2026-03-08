from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl

LOREM_EN = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer non erat vitae dolor placerat gravida. "
    "Proin aliquet, massa vitae sodales consequat, est metus dapibus libero, eget pulvinar magna lorem vel metus. "
    "Praesent ullamcorper, ante non mollis efficitur, nisl ex finibus sapien, vitae volutpat urna lacus vitae nisi. "
    "Suspendisse potenti. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae. "
    "Nunc dictum, lacus eget pulvinar varius, augue leo tristique velit, eget laoreet tellus mauris vitae urna. "
    "Cras interdum, ex ac sodales facilisis, dui arcu ultrices odio, a faucibus erat mauris vitae ligula."
)

LOREM_HE = (
    "לורם איפסום דולור סיט אמט, קונסקטטור אדיפיסינג אלית. סת אמט אלמנטום ניסל סוליסי. "
    "קולורס מונמס קונס אדיפיסינג אלית. קוקו קורוס אוקיי לפתרום. בורמינג אגמון ליחש ערלפקה. "
    "אתור קישור לגלאי, הועיד מא בלי שכמה ושכמהולרם. סחטיר בלמורשך לום, מינסף קוואמן גופה. "
    "צוממר רמא איר, גכח לורם איפסום דולור סיט אמט. מקוט קורוס לופאלר מידינס. "
    "לורם איפסום דולור סיט אמט, קונסקטטור אדיפיסינג אלית, סד דו מגנא אליקו."
)


def render(lang: str) -> None:
    title = get_text("page_titles.home", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    rtl = is_rtl(lang)
    lorem = LOREM_HE if rtl else LOREM_EN
    for _ in range(12):
        st.markdown(lorem)
