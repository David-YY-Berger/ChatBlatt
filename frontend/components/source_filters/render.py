# bs"d - lehagdil torah velahadir
"""
UI rendering for the source-filters component.

Design notes (per product spec):
  * Hierarchy is expressed through real nested containers
    (``st.container(border=True)``), not just indentation.
  * Every nested node (Source Type, Book Category) is collapsed by default.
  * No tri-state/indeterminate checkboxes anywhere – parents just show an
    "x/y selected" count, and an explicit All/None button pair does the
    bulk selection work.
  * Selections are read from/written to a GC-proof store (see
    :mod:`.state`) rather than relying on the checkbox widgets' own
    session_state, since Streamlit discards a widget's state the moment it
    stops being instantiated (i.e. the instant its section is collapsed).
"""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from backend.models_db.Enums import BookCategoryName, PassageType, SourceType

from .data import group_books_by_source_then_category
from .state import (
    DEFAULT_NAMESPACE,
    apply_pending_widget_resets,
    book_key,
    bulk_set,
    category_open_key,
    get_value,
    passage_key,
    set_value,
    srctype_open_key,
)

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


def inject_source_filters_css() -> None:
    """Inject the source-filters CSS from ``assets/source_filters.css``.

    Safe to call multiple times (e.g. once per page) – Streamlit simply
    re-applies the same <style> block.
    """
    css_path = _ASSETS_DIR / "source_filters.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _render_tracked_checkbox(label: str, key: str, namespace: str) -> None:
    """Render a checkbox whose true value lives in the GC-proof store,
    then immediately sync back whatever the user just clicked."""
    current = get_value(key, namespace)
    new_val = st.checkbox(label, value=current, key=key)
    if new_val != current:
        set_value(key, new_val, namespace)


# ---------------------------------------------------------------------------
# Shared header row: title + "x/y selected" + All/None toolbar
# ---------------------------------------------------------------------------

def _render_toolbar_row(
    title: str,
    selected: int,
    total: int,
    all_key: str,
    none_key: str,
    keys: list[str],
    namespace: str,
    toggle: tuple[str, str] | None = None,
) -> bool:
    """Render one header row. If ``toggle`` is given as ``(open_key,
    arrow_button_key)``, also renders a collapse/expand arrow and returns
    the (possibly just-flipped) open state. Otherwise always returns True.
    """
    if toggle is not None:
        open_key, arrow_key = toggle
        is_open = st.session_state.get(open_key, False)
        tog_col, title_col, count_col, all_col, none_col = st.columns([0.5, 2.5, 1.6, 0.8, 0.95])
        with tog_col:
            if st.button("▼" if is_open else "▶", key=arrow_key):
                st.session_state[open_key] = not is_open
                st.rerun()
    else:
        is_open = True
        title_col, count_col, all_col, none_col = st.columns([3.0, 1.6, 0.8, 0.95])

    with title_col:
        st.markdown(f"<div class='sf-node-title'>{title}</div>", unsafe_allow_html=True)
    with count_col:
        st.markdown(f"<div class='sf-count'>{selected}/{total} selected</div>", unsafe_allow_html=True)
    with all_col:
        if st.button("All", key=all_key, help=f"Select all under {title}"):
            bulk_set(keys, True, namespace)
            st.rerun()
    with none_col:
        if st.button("None", key=none_key, help=f"Clear all under {title}"):
            bulk_set(keys, False, namespace)
            st.rerun()

    return is_open


# ---------------------------------------------------------------------------
# Passage type section (flat list, no nesting)
# ---------------------------------------------------------------------------

def render_passage_type_section(namespace: str = DEFAULT_NAMESPACE) -> None:
    """Flat checkbox list for :class:`PassageType`, with an All/None toolbar."""
    # Must run before any checkbox below is instantiated this run – see
    # `state.apply_pending_widget_resets` for why.
    apply_pending_widget_resets(namespace)

    keys = [passage_key(p, namespace) for p in PassageType]
    selected = sum(1 for k in keys if get_value(k, namespace))

    with st.container(border=True, key=f"sf_passage_box_{namespace}"):
        _render_toolbar_row(
            "🔖 Passage Type", selected, len(keys),
            all_key=f"sf_{namespace}_passage_all",
            none_key=f"sf_{namespace}_passage_none",
            keys=keys, namespace=namespace,
        )
        for p in PassageType:
            _render_tracked_checkbox(p.value, passage_key(p, namespace), namespace)


# ---------------------------------------------------------------------------
# Sources section: Source Type -> Book Category -> Book
# (nested via real containers, collapsed by default)
# ---------------------------------------------------------------------------

def _render_category_node(
    src_type: SourceType, category: BookCategoryName, books: list, namespace: str,
) -> None:
    keys = [book_key(b, namespace) for b in books]
    selected = sum(1 for k in keys if get_value(k, namespace))
    open_key = category_open_key(src_type, category, namespace)

    with st.container(border=True, key=f"sf_cat_{namespace}_{src_type.name}_{category.name}"):
        is_open = _render_toolbar_row(
            category.value, selected, len(keys),
            all_key=f"{open_key}_all", none_key=f"{open_key}_none", keys=keys, namespace=namespace,
            toggle=(open_key, f"{open_key}_toggle"),
        )
        if is_open:
            for b in books:
                _render_tracked_checkbox(
                    f"{b.en_display_name} ({b.heb_display_name})",
                    book_key(b, namespace), namespace,
                )


def _render_source_type_node(src_type: SourceType, categories: dict, namespace: str) -> None:
    keys = [book_key(b, namespace) for cat_books in categories.values() for b in cat_books]
    selected = sum(1 for k in keys if get_value(k, namespace))
    open_key = srctype_open_key(src_type, namespace)

    with st.container(border=True, key=f"sf_srctype_{namespace}_{src_type.name}"):
        is_open = _render_toolbar_row(
            src_type.value, selected, len(keys),
            all_key=f"{open_key}_all", none_key=f"{open_key}_none", keys=keys, namespace=namespace,
            toggle=(open_key, f"{open_key}_toggle"),
        )
        if is_open:
            for category, books in categories.items():
                _render_category_node(src_type, category, books, namespace)


def render_sources_section(namespace: str = DEFAULT_NAMESPACE) -> None:
    """Nested Source Type -> Book Category -> Book checkbox tree."""
    # Must run before any checkbox below is instantiated this run – see
    # `state.apply_pending_widget_resets` for why.
    apply_pending_widget_resets(namespace)

    tree = group_books_by_source_then_category()
    all_keys = [
        book_key(b, namespace)
        for categories in tree.values()
        for books in categories.values()
        for b in books
    ]
    selected = sum(1 for k in all_keys if get_value(k, namespace))

    with st.container(border=True, key=f"sf_sources_box_{namespace}"):
        _render_toolbar_row(
            "📚 Sources", selected, len(all_keys),
            all_key=f"sf_{namespace}_sources_all",
            none_key=f"sf_{namespace}_sources_none",
            keys=all_keys, namespace=namespace,
        )
        for src_type, categories in tree.items():
            _render_source_type_node(src_type, categories, namespace)


# ---------------------------------------------------------------------------
# Public panel entry point
# ---------------------------------------------------------------------------

def render_source_filters(namespace: str = DEFAULT_NAMESPACE) -> None:
    """Render the full left-hand source-filter widget: Passage Type + Sources.

    Self-contained – safe to drop onto any page. Call
    :func:`inject_source_filters_css` once per page before this.
    """
    render_passage_type_section(namespace)
    render_sources_section(namespace)
