# bs"d - lehagdil torah velahadir

"""
PersonSelectorComponent

Reusable Streamlit component that renders a person combobox + "Go" button,
matching the same UX pattern used in the Entity Search page.

Usage:
    from components.person_selector import render_person_selector

    selected_key = render_person_selector(lang, state_key="genealogy_person")
    if selected_key:
        # use selected_key …
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from translations1 import get_text, is_rtl


def render_person_selector(
    lang: str,
    state_key: str = "selected_person_key",
) -> Optional[str]:
    """
    Render a person combobox + Go button.

    Loads person select-options from the DB (cached in session state).
    On "Go", persists the selected entity key under `state_key` in session state.

    Args:
        lang:      Current UI language code.
        state_key: Session-state key used to store the confirmed selection.
                   Callers with multiple selectors on one page should use
                   distinct keys to avoid collisions.

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

    rtl = is_rtl(lang)
    placeholder = get_text("ui.select_option", lang)

    display_labels = [placeholder] + [_format_label(opt, rtl) for opt in options]
    key_map = {_format_label(opt, rtl): opt.key for opt in options}

    col_combo, col_btn = st.columns([4, 1])

    with col_combo:
        chosen_label = st.selectbox(
            get_text("entity_search_ui.select_entity", lang),
            options=display_labels,
            index=0,
            key=f"person_selector_combo_{state_key}",
            label_visibility="collapsed",
        )

    has_selection = chosen_label != placeholder
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

    return st.session_state.get(state_key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_label(opt, rtl: bool) -> str:
    if rtl and opt.display_heb_name:
        return f"{opt.display_heb_name} ({opt.display_en_name})"
    if opt.display_heb_name:
        return f"{opt.display_en_name} ({opt.display_heb_name})"
    return opt.display_en_name


def _load_person_options(handler) -> list:
    """Load person select options, cached per Streamlit session."""
    cache_key = "_person_selector_options_cache"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = handler.get_select_options()
    return st.session_state[cache_key]
