# bs"d - lehagdil torah velahadir

"""
PersonSelectorComponent

Reusable Streamlit component: metadata filters (faith, gender, individual/group,
roles; from components/entity_filters.py) + person combobox + "Go" button,
matching the Entity Search people tab. Used by the genealogy and studied-from trees.

Usage:
    from components.person_selector import render_person_selector

    selected_key = render_person_selector(lang, state_key="genealogy_person")
    if selected_key:
        # use selected_key …
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from translations1 import get_text
from components.entity_filters import render_person_filters
from components.entity_option_labels import unique_entity_option_labels


@st.fragment
def render_person_selector(
    lang: str,
    state_key: str = "selected_person_key",
    override_key: Optional[str] = None,
) -> Optional[str]:
    """
    Render a person combobox + Go button.

    Loads person select-options from the DB (cached in session state).
    On "Go", persists the selected entity key under `state_key` in session state.

    Args:
        lang:         Current UI language code.
        state_key:    Session-state key used to store the confirmed selection.
                      Callers with multiple selectors on one page should use
                      distinct keys to avoid collisions.
        override_key: If provided, force the selection to this entity key
                      (e.g. a person picked by clicking a node on a graph)
                      before the widgets are rendered, so both the confirmed
                      selection and the combobox display stay in sync.

    Returns:
        The entity key string of the confirmed selection, or None.
    """
    from backend.app.controllers.entity_search.entity_search_controller import (
        get_entity_search_handler,
    )

    handler = get_entity_search_handler("people")
    if handler is None:
        st.warning(get_text("entity_search_ui.not_implemented", lang))
        return None

    options = _load_person_options(handler)
    if not options:
        st.info(get_text("entity_search_ui.no_entities", lang))
        return None

    # Metadata filters (faith / gender / individual-group / roles), same as Entity Search
    filtered = render_person_filters(options, lang, key_prefix=f"person_selector_filter_{state_key}")

    # Reset the combobox when the filtered set changes (its old choice may be gone)
    signature = tuple(sorted(opt.key for opt in filtered))
    sig_key = f"_person_selector_sig_{state_key}"
    generation_key = f"_person_selector_combo_generation_{state_key}"
    if st.session_state.get(sig_key) != signature:
        st.session_state[generation_key] = st.session_state.get(generation_key, 0) + 1
        st.session_state[sig_key] = signature
    combo_state_key = f"person_selector_combo_{state_key}_{st.session_state.get(generation_key, 0)}"

    if not filtered:
        st.warning(get_text("entity_filters.no_matches", lang))

    placeholder = get_text("ui.select_option", lang)

    display_labels = unique_entity_option_labels(filtered)
    key_map = {label: opt.key for label, opt in zip(display_labels, filtered)}
    localized_labels = dict(zip(display_labels, unique_entity_option_labels(filtered, lang)))

    if override_key:
        st.session_state[state_key] = override_key
        for label, key in key_map.items():
            if key == override_key:
                st.session_state[combo_state_key] = label
                break

    col_combo, col_btn = st.columns([4, 1])

    with col_combo:
        chosen_label = st.selectbox(
            get_text("entity_search_ui.select_entity", lang),
            options=display_labels,
            format_func=lambda label: localized_labels[label],
            index=None,
            placeholder=placeholder,
            key=combo_state_key,
            label_visibility="collapsed",
        )

    has_selection = chosen_label is not None
    entity_key = key_map.get(chosen_label, "") if has_selection else ""

    with col_btn:
        go_clicked = st.button(
            get_text("entity_search_ui.go_button", lang),
            disabled=not has_selection,
            key=f"person_selector_go_{state_key}",
            type="primary",
        )

    if go_clicked and entity_key:
        st.session_state[state_key] = entity_key
        st.rerun()

    return st.session_state.get(state_key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_person_options(handler) -> list:
    """Load person select options, cached per Streamlit session."""
    cache_key = "_person_selector_options_cache"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = handler.get_select_options()
    return st.session_state[cache_key]
