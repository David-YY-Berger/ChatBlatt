from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl

LOREM_EN = (
    "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, "
    "eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam "
    "voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. "
    "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem."
)

LOREM_HE = (
    "לורם איפסום דולור סיט אמט, קונסקטטור אדיפיסינג אלית. סת אמט אלמנטום ניסל סוליסי. "
    "קולורס מונמס קונס אדיפיסינג אלית. קוקו קורוס אוקיי לפתרום. בורמינג אגמון ליחש ערלפקה. "
    "אתור קישור לגלאי, הועיד מא בלי שכמה ושכמהולרם. סחטיר בלמורשך לום, מינסף קוואמן גופה. "
    "צוממר רמא איר, גכח לורם איפסום דולור סיט אמט. מקוט קורוס לופאלר מידינס."
)


def render(lang: str) -> None:
    title = get_text("page_titles.about", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    rtl = is_rtl(lang)
    lorem = LOREM_HE if rtl else LOREM_EN
    for _ in range(10):
        st.markdown(lorem)
