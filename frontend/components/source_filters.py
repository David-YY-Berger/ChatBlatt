# bs"d - lehagdil torah velahadir
"""
Left-hand source filters for the source-search page:

  1. **Passage Type** - a compact list of checkboxes.
  2. **Books** - a multiselect dropdown (same behavior as the entity
     dropdowns) that filters by the source's book.

Selections live in the widgets' own ``session_state`` entries (both widgets
are rendered on every run, so Streamlit never discards them).
"""

from __future__ import annotations

import streamlit as st

from backend.db.data_names.Books import Books
from backend.models_db.Enums import PassageType

_BOOKS_KEY = "book_filter_selected"


def _passage_key(pt: PassageType) -> str:
    return f"passage_filter_{pt.name}"


def _book_options() -> dict[str, str]:
    """``{display label: Book.database_name}`` for every book, in canonical order."""
    options: dict[str, str] = {}
    for b in Books.sorted_all():
        label = b.en_display_name
        if label in options:  # same display name in two source types
            label = f"{label} ({b.source_type.value})"
        options[label] = b.database_name
    return options


def render_source_filters() -> None:
    st.markdown("<div class='entity-select-label'>Passage Type</div>", unsafe_allow_html=True)
    for pt in PassageType:
        st.checkbox(f"{pt.icon} {pt.value}", key=_passage_key(pt))

    st.markdown("<div class='entity-select-label' style='margin-top:0.75rem;'>Books</div>",
                unsafe_allow_html=True)
    st.multiselect(
        "Books",
        options=list(_book_options()),
        key=_BOOKS_KEY,
        label_visibility="collapsed",
        placeholder="Search books…",
    )


def get_selected_passage_types() -> list[PassageType]:
    return [pt for pt in PassageType if st.session_state.get(_passage_key(pt), False)]


def get_selected_book_names() -> list[str]:
    """Selected books as ``Book.database_name`` values (as used in source keys)."""
    options = _book_options()
    return [options[label] for label in st.session_state.get(_BOOKS_KEY, []) if label in options]
