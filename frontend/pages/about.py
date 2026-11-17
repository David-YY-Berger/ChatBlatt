# bs"d - lehagdil torah velahadir

from __future__ import annotations

from html import escape

import streamlit as st

from pages.about_content import LINKEDIN_PROFILE_URL, OPENING_QUOTE, SECTIONS, TABLE_OF_CONTENTS_TITLE
from translations1 import get_text, is_rtl


def _render_table_of_contents(sections: list[tuple[str, str, str]], title: str) -> None:
    links = "".join(
        f'<li><a href="#{escape(section_id, quote=True)}">{escape(section_title)}</a></li>'
        for section_id, section_title, _ in sections
    )
    st.markdown(
        f'<nav class="about-toc" aria-label="{escape(title, quote=True)}">'
        f"<h2>{escape(title)}</h2><ul>{links}</ul></nav>",
        unsafe_allow_html=True,
    )


def render(lang: str) -> None:
    rtl = is_rtl(lang)
    language = "he" if rtl else "en"
    title = get_text("page_titles.about", lang)
    sections = SECTIONS[language]

    st.markdown(f'<div class="page-title">{escape(title)}</div>', unsafe_allow_html=True)
    _render_table_of_contents(sections, TABLE_OF_CONTENTS_TITLE[language])
    if rtl:
        st.markdown(OPENING_QUOTE, unsafe_allow_html=True)

    for section_id, section_title, content in sections:
        st.markdown(
            f'<h2 id="{escape(section_id, quote=True)}" class="about-section-title">'
            f"{escape(section_title)}</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(content)
        if section_id == "about-the-author":
            st.markdown(
                f'<a href="{escape(LINKEDIN_PROFILE_URL, quote=True)}" target="_blank" '
                'rel="noopener noreferrer" aria-label="LinkedIn profile for David Berger" '
                'style="display:inline-flex;align-items:center;gap:0.45rem;text-decoration:none" dir="ltr">'
                '<span aria-hidden="true" '
                'style="display:inline-flex;align-items:center;justify-content:center;width:1.25rem;height:1.25rem;'
                'border-radius:0.2rem;background:#0a66c2;color:white;font-weight:700;font-size:0.8rem">in</span>'
                'LinkedIn</a>',
                unsafe_allow_html=True,
            )
