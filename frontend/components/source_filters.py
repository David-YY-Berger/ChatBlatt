# bs"d - lehagdil torah velahadir
"""
Left-hand source filters for the source-search page:

  1. **Passage Type** - a compact list of checkboxes.
  2. **Source Type** - a compact list of checkboxes; unavailable types are
     disabled and marked as coming soon.

Selections live in the widgets' own ``session_state`` entries (both widgets
are rendered on every run, so Streamlit never discards them).
"""

from __future__ import annotations

import streamlit as st

from backend.models_db.Enums import PassageType, SourceType


def _passage_key(pt: PassageType) -> str:
    return f"passage_filter_{pt.name}"


def _source_type_key(source_type: SourceType) -> str:
    return f"source_type_filter_{source_type.name}"


def render_source_filters() -> None:
    st.markdown("<div class='entity-select-label'>Passage Type</div>", unsafe_allow_html=True)
    for pt in PassageType:
        st.checkbox(f"{pt.icon} {pt.value}", key=_passage_key(pt))

    st.markdown("<div class='entity-select-label' style='margin-top:0.75rem;'>Source Type</div>",
                unsafe_allow_html=True)
    for source_type in SourceType:
        coming_soon = "" if source_type.available else " (Coming soon)"
        st.checkbox(
            f"{source_type.value}{coming_soon}",
            key=_source_type_key(source_type),
            disabled=not source_type.available,
        )


def get_selected_passage_types() -> list[PassageType]:
    return [pt for pt in PassageType if st.session_state.get(_passage_key(pt), False)]


def get_selected_source_types() -> list[SourceType]:
    return [
        source_type for source_type in SourceType
        if source_type.available and st.session_state.get(_source_type_key(source_type), False)
    ]


def set_selected_filters(passage_type_names: list[str], source_type_names: list[str]) -> None:
    """Pre-select the filters (``PassageType`` / available ``SourceType`` names).
    Must run before the filter widgets render in the current script run."""
    for pt in PassageType:
        st.session_state[_passage_key(pt)] = pt.name in passage_type_names
    for source_type in SourceType:
        st.session_state[_source_type_key(source_type)] = (
            source_type.available and source_type.name in source_type_names
        )


def get_selected_passage_type_names() -> list[str]:
    return [pt.name for pt in get_selected_passage_types()]


def get_selected_source_type_names() -> list[str]:
    return [source_type.name for source_type in get_selected_source_types()]
