# bs"d - lehagdil torah velahadir

"""
Entity Search Page.

Abstract rendering pattern:
  - render() dispatches to the correct entity tab (people, places, nations, etc.)
  - _render_entity_search_tab() is the shared template: filters + combobox + Go button + detail view
  - Each entity type plugs in via its BaseEntitySearchHandler from the backend
  - Metadata filters (checkboxes / segmented controls) narrow the combobox options
    client-side, using metadata already carried on the cached select-options.

Currently implemented: Person (people tab), Place, Symbol filters. Nations/Tribes have no filters yet.
"""

from __future__ import annotations

import json
import os

import streamlit as st

import navigation
from translations1 import get_text, is_rtl
from components.entity_filters import render_multi_checkbox_filter, render_person_filters
from system_common.SystemFunctions import get_secret
from system_common.UrlPaths import PARAM_ENTITY_ID, PARAM_SOURCE_REL_LABEL, PARAM_SOURCE_RELS
from system_common.Constants import (
    PAGE_PEOPLE, PAGE_PLACES, PAGE_NATIONS, PAGE_TRIBES, PAGE_SYMBOLS, PAGE_SOURCE_SEARCH,
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


def _render_entity_type_selector(selected: str | None, lang: str) -> None:
    """Row of buttons so the user can pick the entity type without the top navigation menu."""
    st.markdown(f"**{get_text('entity_search_ui.choose_entity', lang)}**")
    tabs = (PAGE_PEOPLE, PAGE_PLACES, PAGE_NATIONS, PAGE_TRIBES, PAGE_SYMBOLS)
    for column, tab in zip(st.columns(len(tabs)), tabs):
        with column:
            if st.button(
                get_text(f"entity_tabs.{tab}", lang),
                key=f"entity_type_btn_{tab}_{lang}",
                type="primary" if tab == selected else "secondary",
                use_container_width=True,
            ) and tab != selected:
                navigation.go(tab)


# =============================================================================
#  Shared entity search template
# =============================================================================

def _render_entity_search_tab(entity_tab: str, lang: str) -> None:
    """
    Renders the shared entity-search UI for any entity type:
      1. Metadata filters (entity-type-specific), narrowing the combobox options
      2. Combobox to pick an entity
      3. Go button (disabled until selection)
      4. Detail view with DB fields + transient relationship lists
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

    # ---- Metadata filters (entity-type-specific) ----
    filtered_options = _render_filters(entity_tab, options, lang)

    # ---- Reset the combobox selection whenever the filtered set changes ----
    # (avoids referencing a previously-chosen label that's no longer in `options`)
    filter_signature = tuple(sorted(opt.key for opt in filtered_options))
    signature_state_key = f"_entity_filter_sig_{entity_tab}"
    if st.session_state.get(signature_state_key) != filter_signature:
        st.session_state.pop(f"entity_combo_{entity_tab}", None)
        st.session_state[signature_state_key] = filter_signature

    if not filtered_options:
        st.warning(get_text("entity_filters.no_matches", lang))

    # ---- Build display labels for combobox ----
    rtl = is_rtl(lang)
    placeholder = get_text("ui.select_option", lang)

    display_labels = [_format_option_label(opt, rtl) for opt in filtered_options]
    key_map = {_format_option_label(opt, rtl): opt.key for opt in filtered_options}

    # ---- Layout: combobox + go button ----
    col_combo, col_btn = st.columns([4, 1])

    with col_combo:
        chosen_label = st.selectbox(
            get_text("entity_search_ui.select_entity", lang),
            options=display_labels,
            index=None,
            placeholder=placeholder,
            key=f"entity_combo_{entity_tab}",
            label_visibility="collapsed",
        )

    has_selection = chosen_label is not None
    entity_key = key_map.get(chosen_label, "") if has_selection else ""

    with col_btn:
        go_clicked = st.button(
            get_text("entity_search_ui.go_button", lang),
            disabled=not has_selection,
            key=f"go_btn_{entity_tab}",
            type="primary",
        )

    # ---- Persist selection in the URL on Go (so the page link is shareable) ----
    if go_clicked and entity_key:
        st.query_params[PARAM_ENTITY_ID] = entity_key

    selected_key = st.query_params.get(PARAM_ENTITY_ID)
    if not selected_key:
        return

    # ---- Fetch & display entity detail ----
    st.divider()
    _render_entity_detail(handler, selected_key, lang)


# =============================================================================
#  Metadata filters
# =============================================================================

def _render_filters(entity_tab: str, options: list, lang: str) -> list:
    """
    Render entity-type-specific metadata filters and return the filtered
    subset of `options`. Filters are read from/written to st.session_state so
    they persist across reruns. Tabs without filters (nations, tribes) return
    `options` unchanged.
    """
    if entity_tab == PAGE_PEOPLE:
        return render_person_filters(options, lang)
    if entity_tab == PAGE_PLACES:
        from backend.models_db.Enums import PlaceType
        return _render_type_filter(
            options, lang, attr="placeType", enum_cls=PlaceType,
            label_key="entity_filters.place_type_label",
            all_key="entity_filters.place_type_all",
            state_prefix="filter_place_type",
        )
    if entity_tab == PAGE_SYMBOLS:
        from backend.models_db.Enums import SymbolType
        return _render_type_filter(
            options, lang, attr="symbolType", enum_cls=SymbolType,
            label_key="entity_filters.symbol_type_label",
            all_key="entity_filters.symbol_type_all",
            state_prefix="filter_symbol_type",
        )
    return options


def _render_type_filter(
    options: list,
    lang: str,
    attr: str,
    enum_cls,
    label_key: str,
    all_key: str,
    state_prefix: str,
) -> list:
    """Generic 'checkbox per enum member + All' filter for a single entity attribute
    (e.g. Place.placeType, Symbol.symbolType)."""
    with st.container(border=True):
        st.markdown(f"**{get_text('entity_filters.section_title', lang)}**")
        # Keep the vertically-stacked checkbox list narrow/compact rather than
        # spanning the full container width (wasted space to the right is OK).
        narrow_col, _ = st.columns([1, 3])
        with narrow_col:
            selected = render_multi_checkbox_filter(
                enum_cls=enum_cls,
                label_key=label_key,
                all_key=all_key,
                state_prefix=state_prefix,
                lang=lang,
            )

    if selected is None:
        return options
    return [opt for opt in options if getattr(opt, attr, None) in selected]


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

    # ---- Metadata badges (entity-type-specific): compact, colorful chips ----
    badges = handler.get_metadata_badges(entity)
    _render_metadata_badges(badges, lang)

    st.divider()

    # ---- Transient relationship fields ----
    transient_labels = handler.get_transient_field_labels()
    _render_relationship_fields(entity, transient_labels, lang)


def _render_metadata_badges(badges: list[dict], lang: str) -> None:
    """
    Render entity metadata (time period, gender, faith, group/individual,
    roles, place type, symbol type, etc.) as a compact, colorful, wrapping
    row of pill-shaped badges instead of a plain key/value grid.

    Each badge dict has: icon, text (raw, language-agnostic) OR label_key
    (translated), and color (hex, drives tint/border/text color).
    """
    if not badges:
        return

    chips = []
    for badge in badges:
        text = badge.get("text") or get_text(badge.get("label_key") or "", lang)
        icon = badge.get("icon", "")
        color = badge.get("color", "#6b7280")
        chips.append(
            "<span style='display:inline-flex; align-items:center; gap:0.35rem; "
            f"background:{color}1f; border:1px solid {color}; color:{color}; "
            "padding:0.28rem 0.7rem; border-radius:999px; font-size:0.85rem; "
            f"font-weight:600; white-space:nowrap;'>{icon} {text}</span>"
        )

    st.markdown(
        "<div style='display:flex; flex-wrap:wrap; gap:0.4rem; margin-bottom:0.6rem;'>"
        + "".join(chips) + "</div>",
        unsafe_allow_html=True,
    )


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
                _render_relationship_list(label, values, field_name, rel_links, lang, entity)


def _render_relationship_list(
    title: str,
    items: list[str],
    field_name: str,
    rel_links: dict,
    lang: str,
    entity=None,
) -> None:
    """
    Render a titled list of related entities.
    Each item is a popover button that shows action options:
      1. View Entity — navigates to the entity's page
      2. View Sources of Relationship — opens Source Search filtered by the relationship's rel keys
    """
    with st.container(border=True):
        st.markdown(
            f"<div style='font-weight:600; font-size:0.95rem; "
            f"color:var(--accent,#1f6feb); margin-bottom:0.4rem;'>"
            f"{title} ({len(items)})</div>",
            unsafe_allow_html=True,
        )
        for item in items:
            rel_keys = (getattr(entity, "rel_keys_by_field", {}) or {}).get(field_name, {}).get(item)
            _render_entity_item_popover(
                item, field_name, rel_links, lang,
                getattr(entity, "display_en_name", ""), title, rel_keys,
            )


_POPOVER_CSS = """
<style>
div[data-testid="stPopoverBody"]:has(.rel-pop-marker) {
    min-width: 0; width: 13rem; padding: 0.4rem 0.5rem;
}
div[data-testid="stPopoverBody"]:has(.rel-pop-marker) [data-testid="stVerticalBlock"] { gap: 0.25rem; }
div[data-testid="stPopoverBody"]:has(.rel-pop-marker) button {
    min-height: 0; padding: 0.3rem 0.6rem; font-size: 0.85rem;
}
</style>
"""


def _render_entity_item_popover(
    item_name: str,
    field_name: str,
    rel_links: dict,
    lang: str,
    entity_name: str = "",
    rel_label: str = "",
    rel_keys: list[str] | None = None,
) -> None:
    """Render a single related-entity name as a compact popover with two actions:
    view the entity, or view the sources of the relationship."""
    link_info = rel_links.get(item_name)  # (entity_key, EntityType) | None
    uid = f"{field_name}_{abs(hash(item_name))}"
    view_label = f"👁 {get_text('entity_search_ui.view_entity', lang)}"

    with st.popover(f"• {item_name}", use_container_width=True):
        st.markdown("<span class='rel-pop-marker'></span>" + _POPOVER_CSS, unsafe_allow_html=True)

        tab_key = _entity_type_to_tab(link_info[1]) if link_info else None
        if tab_key:
            if st.button(view_label, key=f"nav_{uid}", use_container_width=True):
                navigation.go(tab_key, **{PARAM_ENTITY_ID: link_info[0]})
        else:
            st.button(
                view_label,
                key=f"nav_disabled_{uid}",
                use_container_width=True,
                disabled=True,
                help=get_text("entity_search_ui.nav_not_available", lang),
            )

        if st.button(
            f"📄 {get_text('entity_search_ui.view_sources', lang)}",
            key=f"src_{uid}",
            use_container_width=True,
            disabled=not rel_keys,
        ):
            navigation.go(PAGE_SOURCE_SEARCH, **{
                PARAM_SOURCE_RELS: rel_keys,
                PARAM_SOURCE_REL_LABEL: f"{entity_name} · {rel_label} · {item_name}",
            })


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
