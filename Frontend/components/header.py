# bs"d - lehagdil torah velahadir

from __future__ import annotations

import streamlit as st

from translations1 import get_text


def render_header(lang: str) -> None:
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-dedication"><em>{get_text('app.dedication', lang)}</em></div>
            <h1 class="app-title">{get_text('app.title', lang)}</h1>
            <div class="app-subtitle">{get_text('app.subtitle', lang)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
