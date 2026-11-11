# bs"d - lehagdil torah velahadir
"""
Source-search page.

UI responsibilities only:
  - layout (facets column + main column)
  - search input / button / status message
  - result display

All search logic lives in :mod:`pages.source_search_logic`.
Entity-type filter widgets live in :mod:`components.facets`.
Source-filter widgets (Passage Type + Source Type) live in
:mod:`components.source_filters`.
"""

from __future__ import annotations

from dataclasses import replace
import logging
import math

import streamlit as st
import streamlit.components.v1 as components

from translations1 import enum_text, get_text
from backend.models_db.Enums import PassageType
from backend.file_utils.HtmlWriter import HtmlWriter
from components.facets import (
    get_selected_entity_names,
    inject_facet_css,
    preload_all_entity_options,
    render_entity_facets,
)
from components.pdf_export import build_results_pdf, results_pdf_filename
from components.source_filters import render_source_filters
from pages.source_search_logic import (
    clear_relationship_search,
    collect_search_query,
    get_relationship_search,
    current_search_url,
    run_search,
    sync_url_with_search,
    apply_url_params,
)

logger = logging.getLogger(__name__)


def _execute_search(query_obj=None, page: int = 0) -> None:
    try:
        base_query = query_obj or collect_search_query()
        paged_query = replace(
            base_query,
            offset=page * base_query.max_sources,
        )
        ans, elapsed = run_search(paged_query)
        st.session_state["_search_ans"] = ans
        st.session_state["_search_query"] = replace(base_query, offset=0)
        st.session_state["_search_page"] = page
        if query_obj is None:
            st.session_state["_search_entity_names"] = get_selected_entity_names()
            st.session_state["_search_url"] = current_search_url()
            sync_url_with_search()
        st.session_state["_search_elapsed"] = elapsed
        st.session_state.pop("_search_error", None)
    except Exception as e:
        logger.error("Search failed: %s", e)
        st.session_state["_search_error"] = str(e)
        st.session_state.pop("_search_ans", None)
        st.session_state.pop("_search_entity_names", None)


def _render_relationship_chip(lang: str) -> None:
    """Shows the active relationship filter (set from Entity Search) with a clear button."""
    rel_search = get_relationship_search()
    if not rel_search:
        return
    chip_col, clear_col = st.columns([6, 1], vertical_alignment="center")
    with chip_col:
        st.info(f"🔗 {get_text('source_search_ui.relationship_filter', lang)}: **{rel_search['label']}**")
    with clear_col:
        if st.button(get_text("source_search_ui.clear_relationship", lang), key="clear_rel_search"):
            clear_relationship_search()
            st.session_state.pop("_search_ans", None)
            st.rerun()


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
            _execute_search()


def _render_dicta_promo(lang: str) -> None:
    """Note pointing users to Dicta's Talmud/Tanach semantic search engines,
    shown directly below the text-similarity input box."""
    promo = get_text("source_search_ui.dicta_promo", lang).format(
        talmud_link="https://talmudsearch.dicta.org.il/he",
        tanach_link="https://search.dicta.org.il/",
    )
    st.markdown(promo, unsafe_allow_html=False)


def _render_download_button(ans, lang: str) -> None:
    """Large icon-only button that downloads the results as a PDF."""
    entity_names = st.session_state.get("_search_entity_names", [])
    search_url = st.session_state.get("_search_url")
    dedication = get_text("app.dedication", lang)
    st.markdown(
        """<style>
        .st-key-pdf_download button { width:3.4rem; height:3.4rem; font-size:2rem; }
        .st-key-pdf_download button span[data-testid="stIconMaterial"] { font-size:2.2rem; }
        </style>""",
        unsafe_allow_html=True,
    )
    with st.container(key="pdf_download"):
        st.download_button(
            label="\u200b",
            icon=":material/download:",
            data=lambda: build_results_pdf(
                ans,
                search_url,
                entity_names=entity_names,
                dedication=dedication,
                lang=lang,
            ),
            file_name=results_pdf_filename(search_url, entity_names),
            mime="application/pdf",
            help=get_text("source_search_ui.download_pdf", lang),
        )


def _render_search_panel(lang: str) -> None:
    if st.session_state.get("_search_error"):
        st.error(st.session_state["_search_error"])
    elif "_search_ans" in st.session_state:
        ans = st.session_state["_search_ans"]
        found_count = ans.total_sources
        elapsed = st.session_state.get("_search_elapsed", "")
        msg_col, dl_col = st.columns([12, 1], vertical_alignment="center")
        with msg_col:
            st.success(
                f"{get_text('source_search_ui.found_sources', lang).format(count=found_count)} "
                f"{get_text('source_search_ui.search_time', lang).format(elapsed=elapsed)}"
            )
        with dl_col:
            _render_download_button(ans, lang)

    if "_search_ans" in st.session_state:
        _render_pagination(lang)
        _render_results_body(
            st.session_state["_search_ans"],
            st.session_state.get("_search_elapsed", ""),
            lang,
        )


def _render_pagination(lang: str) -> None:
    ans = st.session_state["_search_ans"]
    total_sources = ans.total_sources
    page_size = st.session_state["_search_query"].max_sources
    page_count = max(1, math.ceil(total_sources / page_size))
    page = st.session_state.get("_search_page", 0)
    if page_count <= 1:
        return

    prev_col, page_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        if st.button(
            get_text("source_search_ui.previous_page", lang),
            disabled=page == 0,
            key="source_search_previous_page",
        ):
            _execute_search(st.session_state["_search_query"], page - 1)
            st.rerun()
    with page_col:
        st.markdown(
            get_text("source_search_ui.page_indicator", lang).format(
                page=page + 1, page_count=page_count
            )
        )
        st.caption(
            get_text("source_search_ui.page_help", lang).format(
                start=page * page_size + 1,
                end=min((page + 1) * page_size, total_sources),
                total=total_sources,
            )
        )
    with next_col:
        if st.button(
            get_text("source_search_ui.next_page", lang),
            disabled=page + 1 >= page_count,
            key="source_search_next_page",
        ):
            _execute_search(st.session_state["_search_query"], page + 1)
            st.rerun()


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

def _render_results_body(ans, elapsed: str, lang: str = "en") -> None:
    """Display search results as an HTML component, with a plain-text fallback."""
    html_writer = HtmlWriter()
    try:
        labels = {key: get_text(f"source_display.{key}", lang) for key in ("copy", "hebrew_content", "english_content", "no_content")}
        labels["passage_types"] = {pt.name: enum_text(pt, lang) for pt in PassageType}
        html = html_writer.get_full_html(ans, False, lang, labels)
        components.html(html, height=800, scrolling=True)
        logger.info("Rendered HTML successfully.")
    except Exception as e:
        logger.error("Failed to render HTML: %s", e)
        st.error(f"{get_text('source_search_ui.render_error', lang)}: {e}")
        for src in ans.src_metadata_lst[:20]:
            summary = getattr(src, "summary_heb" if lang == "he" else "summary_en", "") or ""
            st.markdown(f"- **{src.key}** — {summary}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render(lang: str) -> None:
    title = get_text("page_titles.source_search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    # Kick off background fetching of every entity type's select-options list
    # as early as possible (before the rest of the page is built), so the
    # DB round-trips run in parallel with page rendering instead of at
    # click-time. render_entity_facets() below is a no-op if this already ran.
    preload_all_entity_options()

    # Arriving from a shared link / Entity Search: load the URL params into the
    # filter widgets (must happen before they render) and run that search below.
    run_url_search = apply_url_params()

    inject_facet_css()

    left_col, main_col = st.columns([1.6, 6])
    with left_col:
        render_source_filters(lang)
    with main_col:
        # Entity facets at the top of the right area
        render_entity_facets(lang)
        _render_relationship_chip(lang)
        if run_url_search:
            _execute_search()
        # Free-text similarity search below entity filters, with the Find
        # Sources button on the same line, and a Dicta promo note beneath it.
        _render_search_input_row(lang)
        _render_dicta_promo(lang)
        _render_search_panel(lang)
