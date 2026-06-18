# bs"d - lehagdil torah velahadir

from __future__ import annotations

import streamlit as st
from collections import defaultdict

from translations1 import get_text, is_rtl

from system_common.SystemFunctions import get_ts_datetime
# Backend imports to populate facets and to call the search handler
from backend.models_db.Enums import SourceType, PassageType, BookCategoryName
from backend.db.data_names.Books import Books
from backend.app.SearchHandler import SearchHandler
from backend.app.SourceSearchQuery import SourceSearchQuery
from backend.file_utils.HtmlWriter import HtmlWriter
import streamlit.components.v1 as components

from frontend.app import logger

_ENTITIES = [
    ("Animal", "Animal"),
    ("Food", "Food"),
    ("Nation", "Nation"),
    ("Number", "Number"),
    ("Person", "Person"),
    ("Place", "Place"),
    ("Plant", "Plant"),
    ("Symbol", "Symbol"),
    ("TribeOfIsrael", "Tribe Of Israel"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _group_books_by_category() -> dict[BookCategoryName, list]:
    grouped = defaultdict(list)
    for b in Books.sorted_all():
        grouped[b.category].append(b)
    return grouped


# ---------------------------------------------------------------------------
# Facet renderers
# ---------------------------------------------------------------------------

def _render_source_type_facet() -> None:
    st.markdown("**Source Type**")
    for stype in SourceType:
        st.checkbox(stype.value, key=f"facet_src_type_{stype.name}", value=False)


def _render_book_facet() -> None:
    st.markdown("**Book**")
    books_by_cat = _group_books_by_category()
    for cat in BookCategoryName:
        books = books_by_cat.get(cat, [])
        if not books:
            continue
        with st.expander(cat.value, expanded=False):
            for b in books:
                st.checkbox(
                    f"{b.en_display_name} ({b.heb_display_name})",
                    key=f"facet_book_{b.database_name}",
                    value=False,
                )


def _render_passage_type_facet() -> None:
    st.markdown("**Passage Type**")
    for p in PassageType:
        st.checkbox(p.value, key=f"facet_passage_{p.name}", value=False)


def _render_entity_facets() -> None:
    st.markdown("**Entities**")
    for ent_key, ent_label in _ENTITIES:
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(ent_label)
        with cols[1]:
            if st.button("Select", key=f"select_ent_{ent_key}"):
                # open blank popover/modal for now (placeholder)
                with st.popover("Select entity", use_container_width=True):
                    st.write("")


def _render_facets_panel() -> None:
    st.subheader("Facets")
    _render_source_type_facet()
    _render_book_facet()
    _render_passage_type_facet()
    _render_entity_facets()


# ---------------------------------------------------------------------------
# Search logic helpers
# ---------------------------------------------------------------------------

def _collect_search_query() -> SourceSearchQuery:
    """Read current session-state checkbox values and build a SourceSearchQuery."""
    free_text = st.session_state.get("free_text_query", "")

    selected_src_types = [
        stype for stype in SourceType
        if st.session_state.get(f"facet_src_type_{stype.name}", False)
    ]
    selected_passage_types = [
        p for p in PassageType
        if st.session_state.get(f"facet_passage_{p.name}", False)
    ]
    # Note: Book filtering is handled server-side by SearchHandler.filter_by_book.
    selected_books = [  # noqa: F841  (passed implicitly via session state / future use)
        b for b in Books.sorted_all()
        if st.session_state.get(f"facet_book_{b.database_name}", False)
    ]

    return SourceSearchQuery(
        free_text_similarity=free_text,
        max_sources=50,
        src_types=selected_src_types,
        passage_types=selected_passage_types,
        entity_ids=[],
        rel_ids=[],
    )


def _run_search(query_obj: SourceSearchQuery):

    handler = SearchHandler()
    time_begin = get_ts_datetime()
    logger.info("Starting search with SearchHandler.get_full_answer. search start time: " + str(time_begin))

    with st.spinner("Searching..."):
        ans = handler.get_full_answer(query_obj)

    time_end = get_ts_datetime()
    elapsed = str(time_end - time_begin)
    found_count = len(getattr(ans, "src_metadata_lst", []))
    logger.info(f"Search completed. Found {found_count} sources. total search time: {elapsed}")
    return ans, elapsed


def _render_results(ans, elapsed: str) -> None:
    """Display search results: success banner + HTML component, with a plain-text fallback."""
    found_count = len(getattr(ans, "src_metadata_lst", []))
    st.success(f"Found {found_count} sources in {elapsed}")

    html_writer = HtmlWriter()
    try:
        html = html_writer.get_full_html(ans)
        components.html(html, height=800, scrolling=True)
        logger.info("Rendered HTML successfully.")
    except Exception as e:
        logger.error(f"Failed to render HTML: {e}")
        st.error(f"Failed to render HTML: {e}")
        for src in ans.src_metadata_lst[:20]:
            st.markdown(f"- **{src.key}** — {getattr(src, 'summary_en', '')}")


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

def _render_search_panel() -> None:
    st.markdown("<div style='display:flex; justify-content:center'>", unsafe_allow_html=True)
    st.text_input("text similarity search", key="free_text_query")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Find Sources"):
        try:
            query_obj = _collect_search_query()
            ans, elapsed = _run_search(query_obj)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            st.error(f"Search failed: {e}")
            return
        _render_results(ans, elapsed)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render(lang: str) -> None:
    title = get_text("page_titles.source_search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    _rtl = is_rtl(lang)  # available for future RTL layout adjustments

    left_col, main_col = st.columns([2, 6])
    with left_col:
        _render_facets_panel()
    with main_col:
        _render_search_panel()
