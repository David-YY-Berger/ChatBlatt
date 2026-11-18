# bs"d - lehagdil torah velahadir
"""Instructions for connecting an AI chat to Eitz Habina."""

import os
from pathlib import Path

import streamlit as st

from translations1 import get_text, is_rtl

MCP_URL = "https://eitz-habina-prod.up.railway.app/mcp"
MCP_SCREENSHOT = Path(__file__).resolve().parents[1] / "icons" / "optimized" / "mcp-in-chat.png"


def render(lang: str) -> None:
    direction = "rtl" if is_rtl(lang) else "ltr"
    alignment = "right" if is_rtl(lang) else "left"
    st.markdown(
        f"""
        <style>
        .st-key-mcp_page {{ direction: {direction}; text-align: {alignment}; }}
        .st-key-mcp_page [data-testid="stCodeBlock"] {{ direction: ltr; text-align: left; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="mcp_page"):
        title = get_text("page_titles.mcp", lang)
        st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
        if os.environ.get("MCP_ENABLED") == "false":
            st.warning(get_text("mcp_ui.disabled", lang))
            return
        st.markdown(get_text("mcp_ui.introduction", lang))
        st.markdown(get_text("mcp_ui.capabilities", lang))
        st.subheader(get_text("mcp_ui.setup_title", lang))
        st.markdown(get_text("mcp_ui.step_one", lang))
        st.markdown(get_text("mcp_ui.step_two", lang))
        st.code(MCP_URL, language=None)
        st.markdown(get_text("mcp_ui.step_three", lang))
        st.markdown(get_text("mcp_ui.step_four", lang))
        st.subheader(get_text("mcp_ui.examples_title", lang))
        st.caption(get_text("mcp_ui.examples_note", lang))
        for example in (
            "tiberias",
            "number_40",
            "almonds",
            "genealogy",
            "shabbat_disputes",
            "moab",
            "king_david",
        ):
            with st.expander(get_text(f"mcp_ui.example_{example}_prompt", lang)):
                st.markdown(get_text(f"mcp_ui.example_{example}_result", lang))
        st.caption(get_text("mcp_ui.availability", lang))
        st.caption(get_text("mcp_ui.privacy", lang))
        st.image(
            MCP_SCREENSHOT,
            caption=get_text("mcp_ui.screenshot_caption", lang),
            width="stretch",
        )
