# bs"d - lehagdil torah velahadir

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from translations1 import get_text


def render_header(lang: str, main_image_path: Path) -> None:
    main_image_data = base64.b64encode(main_image_path.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-header-row">
                <div class="app-header-titles">
                    <div class="app-dedication"><em>{get_text('app.dedication', lang)}</em></div>
                    <h1 class="app-title">
                        <a class="app-home-link" href="/" target="_self">
                            <span>{get_text('app.title', lang)}</span>
                            <img class="app-main-icon" src="data:image/jpeg;base64,{main_image_data}" alt="{get_text('app.title', lang)}" />
                        </a>
                        <span class="beta-badge">{get_text('app.beta', lang)}</span>
                    </h1>
                    <div class="app-subtitle">{get_text('app.subtitle', lang)}</div>
                </div>
                <a class="app-sefaria-banner" href="https://www.sefaria.org" target="_blank" rel="noopener noreferrer">
                    <img src="https://github.com/user-attachments/assets/0495eb35-9ce9-40d7-9424-8a1f8910ca6b" alt="{get_text('app.sefaria_alt', lang)}" />
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
