# bs"d - lehagdil torah velahadir

"""
Entity Search Page.

Abstract rendering pattern:
  - render() dispatches to the correct entity tab (people, places, nations, etc.)
  - _render_entity_search_tab() is the shared template: combobox + Go button + detail view
  - Each entity type plugs in via its BaseEntitySearchHandler from the backend

Currently implemented: Person (people tab).
"""

from __future__ import annotations

import json
import os

import streamlit as st

from translations1 import get_text, is_rtl
from system_common.SystemFunctions import get_secret
from system_common.Constants import (
    PAGE_PEOPLE, PAGE_PLACES, PAGE_NATIONS, PAGE_TRIBES, PAGE_SYMBOLS,
)

_DEBUG_FE = get_secret("PRINT_DEBUG_LOGS_FE").strip().lower() == "true"


def render(lang: str, selected: str | None = None) -> None:
    """Entry point called from app.py. `selected` is the entity tab key (people, places, etc.)."""
    # Page title
    if selected:
        title_key = f"page_titles.{selected}"
    else:
        title_key = "page_titles.entity_search"

    title = get_text(title_key, lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    if selected is None:
        # No specific tab selected — show a prompt
        st.info(get_text("entity_search_ui.select_tab_prompt", lang))
        return

    _render_entity_search_tab(selected, lang)


# =============================================================================
#  Shared entity search template
# =============================================================================

def _render_entity_search_tab(entity_tab: str, lang: str) -> None:
    """
    Renders the shared entity-search UI for any entity type:
      1. Combobox to pick an entity
      2. Go button (disabled until selection)
      3. Detail view with DB fields + transient relationship lists
    """
    from backend.app.controllers.entity_search.entity_search_controller import get_entity_search_handler

    handler = get_entity_search_handler(entity_tab)
    if handler is None:
        st.warning(get_text("entity_search_ui.not_implemented", lang))
        return

    # ---- Fetch select options (cached per tab) ----
    options = _load_select_options(entity_tab, handler)

    if not options:
        st.info(get_text("entity_search_ui.no_entities", lang))
        return

    # ---- Build display labels for combobox ----
    rtl = is_rtl(lang)
    placeholder = get_text("ui.select_option", lang)

    # Build option list: index 0 is the placeholder
    display_labels = [placeholder] + [
        _format_option_label(opt, rtl) for opt in options
    ]
    key_map = {_format_option_label(opt, rtl): opt.key for opt in options}

    # ---- Layout: combobox + go button ----
    col_combo, col_btn = st.columns([4, 1])

    with col_combo:
        chosen_label = st.selectbox(
            get_text("entity_search_ui.select_entity", lang),
            options=display_labels,
            index=0,
            key=f"entity_combo_{entity_tab}",
            label_visibility="collapsed",
        )

    has_selection = chosen_label != placeholder
    entity_key = key_map.get(chosen_label, "") if has_selection else ""

    with col_btn:
        go_clicked = st.button(
            get_text("entity_search_ui.go_button", lang),
            disabled=not has_selection,
            key=f"go_btn_{entity_tab}",
            type="primary",
        )

    # ---- Persist selection in session state on Go ----
    state_key = f"entity_detail_{entity_tab}"
    if go_clicked and entity_key:
        st.session_state[state_key] = entity_key

    selected_key = st.session_state.get(state_key)
    if not selected_key:
        return

    # ---- Fetch & display entity detail ----
    st.divider()
    _render_entity_detail(handler, selected_key, lang)


# =============================================================================
#  Entity detail rendering
# =============================================================================

def _render_entity_detail(handler, entity_key: str, lang: str) -> None:
    """Fetch the full entity and render its detail view."""
    with st.spinner(get_text("entity_search_ui.loading", lang)):
        entity = handler.get_full_entity(entity_key)

    if entity is None:
        st.error(get_text("entity_search_ui.not_found", lang))
        return

    if _DEBUG_FE:
        _debug_log_entity(entity, handler.get_transient_field_labels())

    rtl = is_rtl(lang)

    # ---- Entity header: name + Hebrew name ----
    name_display = entity.display_heb_name if rtl and entity.display_heb_name else entity.display_en_name
    alt_name = entity.display_en_name if rtl and entity.display_heb_name else entity.display_heb_name

    st.markdown(f"### {name_display}")
    if alt_name:
        st.caption(alt_name)

    # ---- Alt names ----
    all_names = entity.all_heb_names if rtl else entity.all_en_names
    if all_names and len(all_names) > 1:
        st.markdown(f"**{get_text('entity_fields.also_known_as', lang)}:** {', '.join(all_names)}")

    # ---- DB fields (entity-type-specific) ----
    db_fields = handler.get_db_field_display(entity)
    if db_fields:
        cols = st.columns(min(len(db_fields), 4))
        for i, (label_key, value) in enumerate(db_fields):
            with cols[i % len(cols)]:
                label = get_text(label_key, lang)
                st.markdown(f"**{label}**")
                st.markdown(value if value else "—")

    st.divider()

    # ---- Transient relationship fields ----
    transient_labels = handler.get_transient_field_labels()
    _render_relationship_fields(entity, transient_labels, lang)


def _render_relationship_fields(entity, transient_labels: list, lang: str) -> None:
    """
    Render all transient (relationship) fields as titled scrollable lists.
    Only shows fields that have data.
    Uses a 3-column grid layout.
    Each item in a list is rendered as a st.popover button with action options.
    """
    # Filter to fields that have data
    fields_with_data = []
    for field_name, label_key in transient_labels:
        values = getattr(entity, field_name, None)
        if values and isinstance(values, list) and len(values) > 0:
            fields_with_data.append((field_name, label_key, values))

    if not fields_with_data:
        st.info(get_text("entity_search_ui.no_relationships", lang))
        return

    # Navigation link map: display_name -> (entity_key, EntityType)
    rel_links = getattr(entity, "rel_links", {})

    # Render in a 3-column grid
    COLS = 3
    for row_start in range(0, len(fields_with_data), COLS):
        row_items = fields_with_data[row_start:row_start + COLS]
        cols = st.columns(COLS)
        for col_idx, (field_name, label_key, values) in enumerate(row_items):
            with cols[col_idx]:
                label = get_text(label_key, lang)
                _render_relationship_list(label, values, field_name, rel_links, lang)


def _render_relationship_list(
    title: str,
    items: list[str],
    field_name: str,
    rel_links: dict,
    lang: str,
) -> None:
    """
    Render a titled list of related entities.
    Each item is a popover button that shows action options:
      1. View Entity — navigates to the entity's page
      2. View Sources of Relationship — shows "coming soon"
    """
    with st.container(border=True):
        st.markdown(
            f"<div style='font-weight:600; font-size:0.95rem; "
            f"color:var(--accent,#1f6feb); margin-bottom:0.4rem;'>"
            f"{title} ({len(items)})</div>",
            unsafe_allow_html=True,
        )
        for item in items:
            _render_entity_item_popover(item, field_name, rel_links, lang)


def _render_entity_item_popover(
    item_name: str,
    field_name: str,
    rel_links: dict,
    lang: str,
) -> None:
    """Render a single related-entity name as a popover button with action choices."""
    link_info = rel_links.get(item_name)  # (entity_key, EntityType) | None

    with st.popover(f"• {item_name}", use_container_width=True):
        # ── Action 1: View Entity ──────────────────────────────────────
        if link_info:
            entity_key, entity_type = link_info
            tab_key = _entity_type_to_tab(entity_type)
            btn_label = get_text("entity_search_ui.view_entity", lang)
            if tab_key:
                if st.button(
                    btn_label,
                    key=f"nav_{tab_key}_{entity_key}_{field_name}",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state["active_page"] = tab_key
                    st.session_state[f"entity_detail_{tab_key}"] = entity_key
                    st.rerun()
            else:
                st.button(
                    btn_label,
                    key=f"nav_disabled_{hash(item_name)}_{field_name}",
                    use_container_width=True,
                    disabled=True,
                    help=get_text("entity_search_ui.nav_not_available", lang),
                )
        else:
            st.button(
                get_text("entity_search_ui.view_entity", lang),
                key=f"nav_nolink_{hash(item_name)}_{field_name}",
                use_container_width=True,
                disabled=True,
            )

        st.divider()

        # ── Action 2: View Sources of Relationship ─────────────────────
        st.button(
            get_text("entity_search_ui.view_sources", lang),
            key=f"src_{hash(item_name)}_{field_name}",
            use_container_width=True,
            disabled=True,
            help=get_text("entity_search_ui.coming_soon", lang),
        )


def _entity_type_to_tab(entity_type) -> str | None:
    """Map an EntityType to its navigation tab key, or None if not yet supported."""
    from backend.models_db.Enums import EntityType

    _TAB_MAP = {
        EntityType.EPerson: PAGE_PEOPLE,
        EntityType.EPlace: PAGE_PLACES,
        EntityType.ENation: PAGE_NATIONS,
        EntityType.ETribeOfIsrael: PAGE_TRIBES,
        EntityType.ESymbol: PAGE_SYMBOLS,
    }
    return _TAB_MAP.get(entity_type)


# =============================================================================
#  Debug logging
# =============================================================================

def _debug_log_entity(entity, transient_labels: list) -> None:
    """
    When PRINT_DEBUG_LOGS_FE=true, prints to console:
      1. The full entity data as JSON.
      2. Each transient relationship field with its list of display names.
    """
    sep = "=" * 60

    # ── 1. Full entity JSON ──────────────────────────────────────────
    try:
        # Pydantic v2
        entity_dict = entity.model_dump()
    except AttributeError:
        # Pydantic v1 fallback
        entity_dict = entity.dict()

    print(f"\n{sep}")
    print(f"[DEBUG FE] Full entity data for: {getattr(entity, 'display_en_name', entity.key)}")
    print(sep)
    print(json.dumps(entity_dict, ensure_ascii=False, indent=2, default=str))

    # ── 2. Transient / relationship fields ───────────────────────────
    print(f"\n{sep}")
    print("[DEBUG FE] Related entities by relationship:")
    print(sep)
    for field_name, label_key in transient_labels:
        values = getattr(entity, field_name, None)
        if values and isinstance(values, list) and len(values) > 0:
            print(f"  {field_name} ({len(values)}):")
            for name in values:
                print(f"    • {name}")
    print(sep + "\n")


# =============================================================================
#  Helpers
# =============================================================================

def _format_option_label(opt, rtl: bool) -> str:
    """Format a select option for display in the combobox."""
    if rtl and opt.display_heb_name:
        return f"{opt.display_heb_name} ({opt.display_en_name})"
    if opt.display_heb_name:
        return f"{opt.display_en_name} ({opt.display_heb_name})"
    return opt.display_en_name


def _load_select_options(entity_tab: str, handler) -> list:
    """
    Load select options, caching in session state to avoid repeated DB calls.
    Cache is keyed by entity_tab. Clear by deleting the session key.
    """
    cache_key = f"_select_options_cache_{entity_tab}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = handler.get_select_options()
    return st.session_state[cache_key]
