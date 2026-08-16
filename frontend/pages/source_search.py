# bs"d - lehagdil torah velahadir
"""
Source-search page.

UI responsibilities only:
  - layout (facets column + main column)
  - search input / button / status message
  - result display

All search logic lives in :mod:`pages.source_search_logic`.
Entity-type filter widgets live in :mod:`components.facets`.
Source-filter widgets (Passage Type + Sources tree) live in
:mod:`components.source_filters`.
"""

from __future__ import annotations

import logging

import streamlit as st
import streamlit.components.v1 as components

from translations1 import get_text, is_rtl
from backend.file_utils.HtmlWriter import HtmlWriter
from components.facets import (
    inject_facet_css,
    preload_all_entity_options,
    render_entity_facets,
)
from components.source_filters import (
    inject_source_filters_css,
    render_active_filter_chips,
    render_source_filters,
)
from .source_search_logic import collect_search_query, run_search

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main search panel
# ---------------------------------------------------------------------------

def _render_search_input_row(lang: str) -> None:
    """Free-text similarity search box, with the Find Sources button on the
    same line, to its right."""
    input_col, btn_col = st.columns([3, 1])
    with input_col:
        st.text_input(
            get_text("source_search_ui.text_similarity_label", lang),
            key="free_text_query",
            placeholder=get_text("source_search_ui.text_similarity_placeholder", lang),
        )
    with btn_col:
        # Spacer so the button lines up with the input box, which has a
        # label rendered above it.
        st.markdown("<div style='height: 1.9rem;'></div>", unsafe_allow_html=True)
        if st.button(get_text("source_search_ui.find_sources_button", lang)):
            try:
                query_obj = collect_search_query()
                ans, elapsed = run_search(query_obj)
                st.session_state["_search_ans"] = ans
                st.session_state["_search_elapsed"] = elapsed
                st.session_state.pop("_search_error", None)
            except Exception as e:
                logger.error("Search failed: %s", e)
                st.session_state["_search_error"] = str(e)
                st.session_state.pop("_search_ans", None)


def _render_dicta_promo(lang: str) -> None:
    """Note pointing users to Dicta's Talmud/Tanach semantic search engines,
    shown directly below the text-similarity input box."""
    promo = get_text("source_search_ui.dicta_promo", lang).format(
        talmud_link="https://talmudsearch.dicta.org.il/he",
        tanach_link="https://search.dicta.org.il/",
    )
    st.markdown(promo, unsafe_allow_html=False)


def _render_search_panel() -> None:
    if st.session_state.get("_search_error"):
        st.error(st.session_state["_search_error"])
    elif "_search_ans" in st.session_state:
        found_count = len(getattr(st.session_state["_search_ans"], "src_metadata_lst", []))
        elapsed = st.session_state.get("_search_elapsed", "")
        st.success(f"Found {found_count} sources in {elapsed}")

    if "_search_ans" in st.session_state:
        _render_results_body(
            st.session_state["_search_ans"],
            st.session_state.get("_search_elapsed", ""),
        )


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

def _render_results_body(ans, elapsed: str) -> None:
    """Display search results as an HTML component, with a plain-text fallback."""
    html_writer = HtmlWriter()
    try:
        html = html_writer.get_full_html(ans, False)
        components.html(html, height=800, scrolling=True)
        logger.info("Rendered HTML successfully.")
    except Exception as e:
        logger.error("Failed to render HTML: %s", e)
        st.error(f"Failed to render HTML: {e}")
        for src in ans.src_metadata_lst[:20]:
            st.markdown(f"- **{src.key}** — {getattr(src, 'summary_en', '')}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render(lang: str) -> None:
    title = get_text("page_titles.source_search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    _rtl = is_rtl(lang)  # available for future RTL layout adjustments

    # Kick off background fetching of every entity type's select-options list
    # as early as possible (before the rest of the page is built), so the
    # DB round-trips run in parallel with page rendering instead of at
    # click-time. render_entity_facets() below is a no-op if this already ran.
    preload_all_entity_options()

    inject_facet_css()
    inject_source_filters_css()

    left_col, main_col = st.columns([2, 6])
    with left_col:
        render_source_filters()
    with main_col:
        # Entity facets at the top of the right area
        render_entity_facets()
        # Free-text similarity search below entity filters, with the Find
        # Sources button on the same line, and a Dicta promo note beneath it.
        _render_search_input_row(lang)
        _render_dicta_promo(lang)
        # Active filter chips – reflect current source-filter selections,
        # shown directly above the results.
        render_active_filter_chips()
        _render_search_panel()
