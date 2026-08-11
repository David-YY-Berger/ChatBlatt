# bs"d - lehagdil torah velahadir
"""
Active filter chips – rendered above the results, reflecting whatever is
currently checked in the source-filters panel. Each chip has an "✕" to
clear just that selection.

Chips are aggregated for readability: if every book in a category (or every
category in a source type) is selected, a single chip represents the whole
group instead of one chip per book.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from .data import group_books_by_source_then_category
from .state import DEFAULT_NAMESPACE, book_key, bulk_set, get_selected_passage_types, get_value, passage_key

_CHIPS_PER_ROW = 5


def _passage_chips(namespace: str) -> list[tuple[str, Callable[[], None]]]:
    chips: list[tuple[str, Callable[[], None]]] = []
    for p in get_selected_passage_types(namespace):
        key = passage_key(p, namespace)
        chips.append((p.value, lambda k=key: bulk_set([k], False, namespace)))
    return chips


def _source_chips(namespace: str) -> list[tuple[str, Callable[[], None]]]:
    tree = group_books_by_source_then_category()
    chips: list[tuple[str, Callable[[], None]]] = []

    for src_type, categories in tree.items():
        src_keys = [book_key(b, namespace) for books in categories.values() for b in books]
        src_selected = sum(1 for k in src_keys if get_value(k, namespace))
        if src_selected == 0:
            continue
        if src_selected == len(src_keys):
            chips.append((src_type.value, lambda ks=src_keys: bulk_set(ks, False, namespace)))
            continue

        for category, books in categories.items():
            cat_keys = [book_key(b, namespace) for b in books]
            cat_selected = sum(1 for k in cat_keys if get_value(k, namespace))
            if cat_selected == 0:
                continue
            if cat_selected == len(cat_keys):
                label = f"{src_type.value}: {category.value}"
                chips.append((label, lambda ks=cat_keys: bulk_set(ks, False, namespace)))
                continue

            for b in books:
                k = book_key(b, namespace)
                if get_value(k, namespace):
                    chips.append((b.en_display_name, lambda kk=k: bulk_set([kk], False, namespace)))

    return chips


def render_active_filter_chips(namespace: str = DEFAULT_NAMESPACE) -> None:
    """Render removable chips for every currently active source filter.

    Intended to be placed directly above the search results. Renders
    nothing when no filters are active.
    """
    chips = _passage_chips(namespace) + _source_chips(namespace)
    if not chips:
        return

    with st.container(key=f"sf_chips_bar_{namespace}"):
        st.markdown("<div class='sf-chips-label'>Active filters:</div>", unsafe_allow_html=True)
        for row_start in range(0, len(chips), _CHIPS_PER_ROW):
            row = chips[row_start:row_start + _CHIPS_PER_ROW]
            cols = st.columns(len(row))
            for i, (col, (label, clear_fn)) in enumerate(zip(cols, row)):
                with col:
                    if st.button(f"{label}  ✕", key=f"sf_chip_{namespace}_{row_start + i}"):
                        clear_fn()
                        st.rerun()
