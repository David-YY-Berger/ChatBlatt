# bs"d - lehagdil torah velahadir
"""Instructions for connecting an AI chat to Eitz Habina."""

import streamlit as st

from translations1 import get_text

MCP_URL = "https://eitz-habina-prod.up.railway.app/mcp"


def render(lang: str) -> None:
    title = get_text("page_titles.mcp", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(get_text("mcp_ui.introduction", lang))
    st.markdown(get_text("mcp_ui.capabilities", lang))
    st.subheader(get_text("mcp_ui.setup_title", lang))
    st.markdown(get_text("mcp_ui.step_one", lang))
    st.markdown(get_text("mcp_ui.step_two", lang))
    st.code(MCP_URL, language=None)
    st.markdown(get_text("mcp_ui.step_three", lang))
    st.markdown(get_text("mcp_ui.step_four", lang))
    st.caption(get_text("mcp_ui.availability", lang))
    st.caption(get_text("mcp_ui.privacy", lang))
