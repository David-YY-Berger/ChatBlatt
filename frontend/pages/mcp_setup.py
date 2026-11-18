# bs"d - lehagdil torah velahadir
"""Instructions for connecting an AI chat to Eitz Habina."""

import os
import re

import streamlit as st

from translations1 import get_text, is_rtl

MCP_URL = "https://eitz-habina-prod.up.railway.app/mcp"
SEFARIA_EXAMPLE_SOURCES = {
    "tiberias": (
        "Sukkah.27a-27b",
        "Berakhot.30b",
        "Berakhot.62a",
        "Chullin.48a-48b",
        "Eruvin.29a",
        "Sanhedrin.93a",
        "Eruvin.101b",
        "Shabbat.115a-115b",
        "Berakhot.53a",
        "Moed_Katan.25a-25b",
        "Zevachim.118b",
        "Pesachim.46a",
    ),
    "number_40": (
        "Sotah.2a",
        "Sanhedrin.22a",
        "Bekhorot.21b",
        "Berakhot.32b",
        "Shabbat.89a",
        "Taanit.7b",
        "Makkot.22b",
        "Taanit.29a",
        "Pirkei_Avot.5.21",
    ),
    "almonds": (
        "Shabbat.152a",
        "Yoma.52b",
        "Horayot.12a",
        "Keritot.5b",
        "Yoma.52a",
        "Chullin.25b",
        "Berakhot.39a",
        "Pesachim.42b",
    ),
    "genealogy": (
        "Genesis.21.1-8",
        "Genesis.25.23-26",
        "Genesis.35.16-26",
        "Genesis.46.8-28",
        "Exodus.6.14-25",
        "Exodus.6.23",
        "Numbers.20.23-29",
        "Exodus.6.25",
        "Numbers.25.7-13",
        "I_Chronicles.5.29-36",
        "Ezra.7.1-5",
        "I_Chronicles.5.30",
        "I_Chronicles.5.31",
        "I_Chronicles.5.38",
        "I_Chronicles.5.39",
        "I_Chronicles.5.40",
        "I_Chronicles.5.27-41",
    ),
    "shabbat_disputes": (
        "Shabbat.31b",
        "Zevachim.91b-92a",
        "Shabbat.42a",
        "Shabbat.19b",
        "Shabbat.45b",
        "Shabbat.45a",
        "Shabbat.29a",
        "Shabbat.124b",
        "Beitzah.31b",
        "Shabbat.39b",
        "Shabbat.92b-93a",
        "Shabbat.136a",
        "Eruvin.95a-95b",
        "Shabbat.128a-128b",
        "Keritot.19b-20a",
    ),
    "moab": (
        "Numbers.24.14-25",
        "Isaiah.15.1-16.14",
        "Jeremiah.48.1-47",
        "Ezekiel.25.8-11",
        "Amos.2.1-3",
        "Zephaniah.2.8-11",
    ),
    "king_david": (
        "I_Samuel.18.27",
        "II_Samuel.3.13-14",
        "Sanhedrin.21a",
        "I_Samuel.25.43",
        "II_Samuel.3.2",
        "I_Chronicles.3.1",
        "I_Samuel.25.42",
        "II_Samuel.3.3",
        "I_Chronicles.3.2",
        "II_Samuel.3.4",
        "I_Chronicles.3.3",
        "II_Samuel.3.5",
        "II_Samuel.11.3",
        "II_Samuel.11.27",
        "I_Chronicles.3.5",
        "II_Samuel.5.13",
        "I_Chronicles.3.9",
        "I_Chronicles.14.3",
        "II_Samuel.3.2-5",
        "I_Chronicles.3.1-3",
        "II_Samuel.12.15-24",
        "II_Samuel.12.15-18",
        "II_Samuel.5.14-16",
        "I_Chronicles.3.6-8",
        "I_Chronicles.14.5-7",
        "I_Chronicles.3.6",
        "I_Chronicles.3.8",
        "I_Chronicles.3.7",
        "I_Chronicles.14.6",
        "II_Samuel.13.1",
        "II_Chronicles.11.18",
    ),
}


def _format_sefaria_ref(ref: str) -> str:
    book, section = ref.split(".", 1)
    if re.match(r"\d+\.\d", section):
        section = section.replace(".", ":")
    return f"{book.replace('_', ' ')} {section.replace('-', '–')}"


def _sefaria_links(example: str, lang: str) -> str:
    label = get_text("mcp_ui.view_in_sefaria", lang)
    title = get_text("mcp_ui.sefaria_links_title", lang)
    links = "\n".join(
        f"- {_format_sefaria_ref(ref)} ([{label}](https://www.sefaria.org/{ref}))"
        for ref in SEFARIA_EXAMPLE_SOURCES[example]
    )
    return f"**{title}:**\n\n{links}"


def render(lang: str) -> None:
    direction = "rtl" if is_rtl(lang) else "ltr"
    alignment = "right" if is_rtl(lang) else "left"
    st.markdown(
        f"""
        <style>
        .st-key-mcp_page {{ direction: {direction}; text-align: {alignment}; }}
        .st-key-mcp_page [data-testid="stCodeBlock"] {{ direction: ltr; text-align: left; }}
        .st-key-mcp_page [data-testid="stCode"] {{ direction: ltr; text-align: left; }}
        .st-key-mcp_page [class*="st-key-mcp_example_answer_"] {{ direction: ltr; text-align: left; }}
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
        st.markdown(
            f"**{get_text('mcp_ui.toc_title', lang)}:** "
            f"[{get_text('mcp_ui.what_is_mcp_title', lang)}](#what-is-mcp) · "
            f"[{get_text('mcp_ui.examples_section_title', lang)}](#real-examples) · "
            f"[{get_text('mcp_ui.setup_title', lang)}](#set-up-your-own-free-mcp)"
        )
        st.subheader(get_text("mcp_ui.what_is_mcp_title", lang), anchor="what-is-mcp")
        st.markdown(get_text("mcp_ui.introduction", lang))
        st.markdown(get_text("mcp_ui.capabilities", lang))
        st.subheader(get_text("mcp_ui.examples_section_title", lang), anchor="real-examples")
        st.caption(get_text("mcp_ui.examples_title", lang))
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
                result = get_text(f"mcp_ui.example_{example}_result", lang)
                with st.container(key=f"mcp_example_answer_{example}"):
                    st.markdown(result)
                st.markdown(_sefaria_links(example, lang))
        st.caption(get_text("mcp_ui.availability", lang))
        st.caption(get_text("mcp_ui.privacy", lang))
        st.subheader(get_text("mcp_ui.setup_title", lang), anchor="set-up-your-own-free-mcp")
        st.markdown(get_text("mcp_ui.step_one", lang))
        st.markdown(get_text("mcp_ui.step_two", lang))
        st.code(MCP_URL, language=None)
        st.markdown(get_text("mcp_ui.step_three", lang))
        st.markdown(get_text("mcp_ui.step_four", lang))
