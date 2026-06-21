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


def _group_books_by_source_then_category() -> dict[SourceType, dict[BookCategoryName, list]]:
    """Returns {SourceType: {BookCategoryName: [Book, ...]}} preserving sorted order."""
    result: dict[SourceType, dict[BookCategoryName, list]] = {}
    for b in Books.sorted_all():
        result.setdefault(b.source_type, {})
        result[b.source_type].setdefault(b.category, [])
        result[b.source_type][b.category].append(b)
    return result


def _inject_facet_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Compact facet checkboxes ── */
        div[data-testid="stCheckbox"] {
            margin-bottom: -10px;
        }

        /* ── Facet section expander: outer container (level 1) ── */
        div[data-testid="stExpander"] {
            border: 1px solid #24354e;
            border-radius: 8px;
            margin-bottom: 6px;
            background-color: #1f2f4a;
        }

        /* ── Facet section expander: header row (level 1) ── */
        div[data-testid="stExpander"] > details > summary,
        div[data-testid="stExpander"] summary {
            font-weight: 700;
            font-size: 0.92rem;
            color: #cdd6f4;
            padding: 6px 10px;
            border-radius: 8px;
        }

        div[data-testid="stExpander"] summary:hover {
            background-color: #2a3f5f;
            border-radius: 8px;
        }

        /* ── Nested expanders: level 2 (e.g. Source Type inside Book) ── */
        div[data-testid="stExpander"] div[data-testid="stExpander"] {
            border: 1px solid #1e3352;
            background-color: #152a42;
        }

        div[data-testid="stExpander"] div[data-testid="stExpander"] summary {
            font-weight: 600;
            font-size: 0.88rem;
            color: #94a3b8;
        }

        /* ── Triply-nested expanders: level 3 (category inside source type) ── */
        div[data-testid="stExpander"] div[data-testid="stExpander"] div[data-testid="stExpander"] {
            border: 1px solid #18304d;
            background-color: #0f1e30;
        }

        div[data-testid="stExpander"] div[data-testid="stExpander"] div[data-testid="stExpander"] summary {
            font-weight: 500;
            font-size: 0.84rem;
            color: #7a8ba8;
        }

        /* ── Select All / None buttons inside facet expanders: compact ── */
        div[data-testid="stExpander"] [data-testid="stButton"] > button {
            padding: 1px 6px !important;
            font-size: 0.72rem !important;
            min-height: 22px !important;
            height: 22px !important;
            border-radius: 4px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Select All / Deselect All helper
# ---------------------------------------------------------------------------

def _render_select_all_buttons(section_key: str, state_keys: list[str]) -> None:
    """Render compact ✓ All / ✗ None buttons that bulk-toggle a set of checkbox keys."""
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("✓ All", key=f"sel_all_{section_key}", use_container_width=True):
            for k in state_keys:
                st.session_state[k] = True
            st.rerun()
    with c2:
        if st.button("✗ None", key=f"sel_none_{section_key}", use_container_width=True):
            for k in state_keys:
                st.session_state[k] = False
            st.rerun()


# ---------------------------------------------------------------------------
# Facet renderers
# ---------------------------------------------------------------------------

def _render_source_type_facet() -> None:
    all_keys = [f"facet_src_type_{stype.name}" for stype in SourceType]
    with st.expander("📄  Source Type", expanded=False):
        _render_select_all_buttons("src_type", all_keys)
        for stype in SourceType:
            st.checkbox(stype.value, key=f"facet_src_type_{stype.name}", value=False)


def _render_book_facet() -> None:
    all_book_keys = [f"facet_book_{b.database_name}" for b in Books.sorted_all()]
    with st.expander("📚  Book", expanded=False):
        _render_select_all_buttons("book_all", all_book_keys)

        books_by_src = _group_books_by_source_then_category()
        for src_type, cats in books_by_src.items():
            src_book_keys = [
                f"facet_book_{b.database_name}"
                for cat_books in cats.values()
                for b in cat_books
            ]
            with st.expander(f"📖  {src_type.value}", expanded=False):
                _render_select_all_buttons(f"book_src_{src_type.name}", src_book_keys)

                for cat, cat_books in cats.items():
                    cat_keys = [f"facet_book_{b.database_name}" for b in cat_books]
                    with st.expander(cat.value, expanded=False):
                        _render_select_all_buttons(
                            f"book_cat_{src_type.name}_{cat.name}", cat_keys
                        )
                        for b in cat_books:
                            st.checkbox(
                                f"{b.en_display_name} ({b.heb_display_name})",
                                key=f"facet_book_{b.database_name}",
                                value=False,
                            )


def _render_passage_type_facet() -> None:
    all_keys = [f"facet_passage_{p.name}" for p in PassageType]
    with st.expander("🔖  Passage Type", expanded=False):
        _render_select_all_buttons("passage_type", all_keys)
        for p in PassageType:
            st.checkbox(p.value, key=f"facet_passage_{p.name}", value=False)


def _render_entity_facets() -> None:
    with st.expander("🏷️  Entities", expanded=False):
        for ent_key, ent_label in _ENTITIES:
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(ent_label)
            with cols[1]:
                if st.button("Select", key=f"select_ent_{ent_key}"):
                    with st.popover("Select entity", use_container_width=True):
                        st.write("")


def _render_facets_panel() -> None:
    _inject_facet_css()
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


def _render_results_body(ans, elapsed: str) -> None:
    """Display search results HTML component, with a plain-text fallback."""
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

    btn_col, msg_col = st.columns([1, 4])
    with btn_col:
        if st.button("Find Sources"):
            try:
                query_obj = _collect_search_query()
                ans, elapsed = _run_search(query_obj)
                st.session_state["_search_ans"] = ans
                st.session_state["_search_elapsed"] = elapsed
                st.session_state.pop("_search_error", None)
            except Exception as e:
                logger.error(f"Search failed: {e}")
                st.session_state["_search_error"] = str(e)
                st.session_state.pop("_search_ans", None)

    with msg_col:
        if st.session_state.get("_search_error"):
            st.error(st.session_state["_search_error"])
        elif "_search_ans" in st.session_state:
            ans = st.session_state["_search_ans"]
            elapsed = st.session_state.get("_search_elapsed", "")
            found_count = len(getattr(ans, "src_metadata_lst", []))
            st.success(f"Found {found_count} sources in {elapsed}")

    if "_search_ans" in st.session_state:
        _render_results_body(
            st.session_state["_search_ans"],
            st.session_state.get("_search_elapsed", ""),
        )


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
