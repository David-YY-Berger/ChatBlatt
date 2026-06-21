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

        /* ── Custom facet header row: kill column gaps and align items ── */
        .facet-header-row > div[data-testid="stHorizontalBlock"] {
            gap: 0 !important;
            align-items: center !important;
            margin-bottom: 0 !important;
        }

        /* ── Custom facet section wrapper ── */
        .facet-section {
            border: 1px solid #24354e;
            border-radius: 8px;
            margin-bottom: 4px;
            background-color: #1f2f4a;
            padding: 2px 6px 4px 6px;
        }

        /* ── All buttons inside the facet panel: ultra-compact ── */
        .facet-section [data-testid="stButton"] > button,
        .facet-header-row [data-testid="stButton"] > button {
            padding: 0px 5px !important;
            font-size: 0.72rem !important;
            min-height: 22px !important;
            height: 22px !important;
            line-height: 1 !important;
            border-radius: 4px !important;
        }

        /* ── Nested facet sections: level 2 (source type inside book) ── */
        .facet-section .facet-section {
            background-color: #152a42;
            border-color: #1e3352;
        }

        /* ── Nested facet sections: level 3 (category inside source type) ── */
        .facet-section .facet-section .facet-section {
            background-color: #0f1e30;
            border-color: #18304d;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Custom collapsible facet section header
# ---------------------------------------------------------------------------

def _selection_status_html(state_keys: list[str]) -> str:
    """Return a coloured HTML badge: ALL / NONE / SOME (n/total)."""
    num_selected = sum(1 for k in state_keys if st.session_state.get(k, False))
    total = len(state_keys)
    if num_selected == total:
        return "<span style='color:#4ade80;font-size:0.70rem;margin-left:6px;font-weight:400'>● ALL</span>"
    elif num_selected == 0:
        return "<span style='color:#64748b;font-size:0.70rem;margin-left:6px;font-weight:400'>○ NONE</span>"
    else:
        return (
            f"<span style='color:#fbbf24;font-size:0.70rem;margin-left:6px;font-weight:400'>"
            f"◑ {num_selected}/{total}</span>"
        )


def _facet_section_header(title: str, section_key: str, state_keys: list[str] | None = None) -> bool:
    """Render a single compact row: [▶/▼] [title + status] [✓] [✗].

    Clicking ▶/▼ toggles expansion; ✓/✗ bulk-toggle checkboxes.
    A coloured badge (ALL / NONE / SOME) is shown next to the title when
    *state_keys* is provided.
    Returns True when the section is currently expanded.
    """
    is_open = st.session_state.get(f"_open_{section_key}", False)
    has_keys = bool(state_keys)

    status_html = _selection_status_html(state_keys) if state_keys else ""

    # Column widths: toggle | label | (✓ | ✗ only when checkboxes exist)
    if has_keys:
        c_tog, c_lbl, c_all, c_none = st.columns([0.35, 3.8, 0.55, 0.55])
        with c_tog:
            arrow = "▼" if is_open else "▶"
            if st.button(arrow, key=f"toggle_{section_key}"):
                st.session_state[f"_open_{section_key}"] = not is_open
                st.rerun()
        with c_lbl:
            st.markdown(
                f"<div style='padding-top:4px;font-weight:700;font-size:0.9rem;color:#cdd6f4'>"
                f"{title}{status_html}</div>",
                unsafe_allow_html=True,
            )
        with c_all:
            if st.button("✓", key=f"sel_all_{section_key}", help="Select all"):
                for k in state_keys:
                    st.session_state[k] = True
                st.rerun()
        with c_none:
            if st.button("✗", key=f"sel_none_{section_key}", help="Deselect all"):
                for k in state_keys:
                    st.session_state[k] = False
                st.rerun()
    else:
        c_tog, c_lbl = st.columns([0.35, 5.0])
        with c_tog:
            arrow = "▼" if is_open else "▶"
            if st.button(arrow, key=f"toggle_{section_key}"):
                st.session_state[f"_open_{section_key}"] = not is_open
                st.rerun()
        with c_lbl:
            st.markdown(
                f"<div style='padding-top:4px;font-weight:700;font-size:0.9rem;color:#cdd6f4'>{title}</div>",
                unsafe_allow_html=True,
            )

    return st.session_state.get(f"_open_{section_key}", False)


# (select-all helper removed – functionality now lives in _facet_section_header)


# ---------------------------------------------------------------------------
# Facet renderers
# ---------------------------------------------------------------------------

def _render_source_type_facet() -> None:
    all_keys = [f"facet_src_type_{stype.name}" for stype in SourceType]
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if _facet_section_header("📄 Source Type", "src_type", all_keys):
        for stype in SourceType:
            st.checkbox(stype.value, key=f"facet_src_type_{stype.name}", value=False)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_book_facet() -> None:
    all_book_keys = [f"facet_book_{b.database_name}" for b in Books.sorted_all()]
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if _facet_section_header("📚 Book", "book_all", all_book_keys):
        books_by_src = _group_books_by_source_then_category()
        for src_type, cats in books_by_src.items():
            src_book_keys = [
                f"facet_book_{b.database_name}"
                for cat_books in cats.values()
                for b in cat_books
            ]
            # ── Source-type level (indented, same facet-section style) ──
            st.markdown('<div class="facet-section" style="margin-left:8px;margin-top:4px;">', unsafe_allow_html=True)
            if _facet_section_header(f"📖 {src_type.value}", f"book_src_{src_type.name}", src_book_keys):
                for cat, cat_books in cats.items():
                    cat_keys = [f"facet_book_{b.database_name}" for b in cat_books]
                    # ── Category level (further indented) ──
                    st.markdown('<div class="facet-section" style="margin-left:16px;margin-top:4px;">', unsafe_allow_html=True)
                    if _facet_section_header(cat.value, f"book_cat_{src_type.name}_{cat.name}", cat_keys):
                        for b in cat_books:
                            st.checkbox(
                                f"{b.en_display_name} ({b.heb_display_name})",
                                key=f"facet_book_{b.database_name}",
                                value=False,
                            )
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_passage_type_facet() -> None:
    all_keys = [f"facet_passage_{p.name}" for p in PassageType]
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if _facet_section_header("🔖 Passage Type", "passage_type", all_keys):
        for p in PassageType:
            st.checkbox(p.value, key=f"facet_passage_{p.name}", value=False)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_entity_facets() -> None:
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if _facet_section_header("🏷️ Entities", "entities"):
        for ent_key, ent_label in _ENTITIES:
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(ent_label)
            with cols[1]:
                if st.button("Select", key=f"select_ent_{ent_key}"):
                    with st.popover("Select entity", use_container_width=True):
                        st.write("")
    st.markdown("</div>", unsafe_allow_html=True)


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
