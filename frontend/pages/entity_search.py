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
from pathlib import Path

import streamlit as st

import navigation
from metrics import admin_params, record_entity_search
from translations1 import enum_text, get_text, is_rtl
from components.entity_filters import render_multi_checkbox_filter, render_person_filters
from components.entity_option_labels import unique_entity_option_labels
from system_common.SystemFunctions import get_secret
from system_common.UrlPaths import (
    PARAM_ENTITY_ID, PARAM_NAVIGATION_ORIGIN, PARAM_SOURCE_REL_LABEL, PARAM_SOURCE_RELS, page_url,
)
from system_common.Constants import (
    PAGE_PEOPLE, PAGE_PLACES, PAGE_NATIONS, PAGE_TRIBES, PAGE_SYMBOLS, PAGE_SOURCE_SEARCH,
    PAGE_FAMILY_TREE,
)

_DEBUG_FE = get_secret("PRINT_DEBUG_LOGS_FE").strip().lower() == "true"
SYMBOLS_WARNING_SHOWN_KEY = "symbols_warning_shown"


def _show_symbols_data_warning(lang: str) -> None:
    @st.dialog(get_text("studied_from_ui.data_quality_title", lang))
    def _dialog() -> None:
        st.warning(get_text("studied_from_ui.data_quality_warning", lang))

    _dialog()


def render(lang: str, selected: str | None = None) -> None:
    """Entry point called from app.py. `selected` is the entity tab key (people, places, etc.)."""
    # Page title
    if selected:
        title_key = f"page_titles.{selected}"
    else:
        title_key = "page_titles.entity_search"

    title = get_text(title_key, lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    if selected == PAGE_SYMBOLS and not st.session_state.get(SYMBOLS_WARNING_SHOWN_KEY):
        st.session_state[SYMBOLS_WARNING_SHOWN_KEY] = True
        _show_symbols_data_warning(lang)

    if selected is None:
        _render_landing(lang)
        return

    _render_entity_search_tab(selected, lang)


_ICON_DIR = Path(__file__).resolve().parents[1] / "icons" / "optimized"
_ENTITY_ICONS = (
    (PAGE_PEOPLE, "entity_search_main.jpg"),
    (PAGE_PLACES, "entity_search_place.jpg"),
    (PAGE_NATIONS, "entity_search_nations.jpg"),
    (PAGE_TRIBES, "entity_search_tribe_of_israel.jpg"),
)


def _render_landing(lang: str) -> None:
    """One clickable card (image + title) per visible entity type."""
    st.markdown(
        f'<div class="home-subtitle">{get_text("entity_search_ui.choose_entity", lang)}</div>',
        unsafe_allow_html=True,
    )
    for column, (tab, icon_name) in zip(st.columns(len(_ENTITY_ICONS)), _ENTITY_ICONS):
        with column:
            with st.container(border=True, key=f"home_tool_entity_{tab}"):
                title = get_text(f"entity_tabs.{tab}", lang)
                st.image(_ICON_DIR / icon_name, width=180)
                st.markdown(f'<div class="home-tool-title">{title}</div>', unsafe_allow_html=True)
                if st.button(title, key=f"entity_landing_btn_{tab}_{lang}", use_container_width=True):
                    navigation.go(tab)


def _render_entity_type_selector(selected: str | None, lang: str) -> None:
    """Row of buttons so the user can pick the entity type without the top navigation menu."""
    st.markdown(f"**{get_text('entity_search_ui.choose_entity', lang)}**")
    tabs = (PAGE_PEOPLE, PAGE_PLACES, PAGE_NATIONS, PAGE_TRIBES)
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

    _render_entity_selector(entity_tab, options, lang)

    selected_key = st.query_params.get(PARAM_ENTITY_ID)
    if not selected_key:
        return

    # ---- Fetch & display entity detail ----
    st.divider()
    _render_entity_detail(handler, selected_key, lang, entity_tab)


@st.fragment
def _render_entity_selector(entity_tab: str, options: list, lang: str) -> None:
    # ---- Metadata filters (entity-type-specific) ----
    filtered_options = _render_filters(entity_tab, options, lang)

    # ---- Reset the combobox selection whenever the filtered set changes ----
    # (avoids referencing a previously-chosen label that's no longer in `options`)
    filter_signature = tuple(sorted(opt.key for opt in filtered_options))
    signature_state_key = f"_entity_filter_sig_{entity_tab}"
    generation_key = f"_entity_combo_generation_{entity_tab}"
    if st.session_state.get(signature_state_key) != filter_signature:
        st.session_state[generation_key] = st.session_state.get(generation_key, 0) + 1
        st.session_state[signature_state_key] = filter_signature
    combo_state_key = f"entity_combo_{entity_tab}_{st.session_state.get(generation_key, 0)}"

    if not filtered_options:
        st.warning(get_text("entity_filters.no_matches", lang))

    # ---- Build display labels for combobox ----
    placeholder = get_text("ui.select_option", lang)

    display_labels = unique_entity_option_labels(filtered_options)
    key_map = {l: o.key for l, o in zip(display_labels, filtered_options)}
    localized_labels = dict(zip(display_labels, unique_entity_option_labels(filtered_options, lang)))

    # ---- Layout: combobox + go button ----
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
            key=f"go_btn_{entity_tab}",
            type="primary",
        )

    # ---- Persist selection in the URL on Go (so the page link is shareable) ----
    if go_clicked and entity_key:
        st.query_params[PARAM_ENTITY_ID] = entity_key
        record_entity_search(entity_tab, entity_key, next(
            (opt.display_en_name for opt in filtered_options if opt.key == entity_key), ""
        ), lang)
        st.session_state["_metrics_entity_url"] = (entity_tab, entity_key)
        st.rerun()


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

def _render_family_tree_button(entity_key: str, lang: str) -> None:
    """Image button (with hover hint) that opens the family tree centred on this person."""
    with st.container(key="tree_link_btn"):
        st.image(_ICON_DIR / "trees.jpg", width=64)
        if st.button(
            get_text("entity_search_ui.open_family_tree", lang),
            key=f"open_family_tree_{entity_key}",
            help=get_text("entity_search_ui.open_family_tree", lang),
        ):
            st.session_state["genealogy_pending_person"] = entity_key
            navigation.go(PAGE_FAMILY_TREE)


def _render_entity_detail(handler, entity_key: str, lang: str, entity_tab: str | None = None) -> None:
    """Fetch the full entity and render its detail view."""
    with st.spinner(get_text("entity_search_ui.loading", lang)):
        entity = handler.get_full_entity(entity_key)

    if entity is None:
        st.error(get_text("entity_search_ui.not_found", lang))
        return

    signature = (entity_tab, entity_key)
    if st.session_state.get("_metrics_entity_url") != signature:
        record_entity_search(entity_tab or "", entity_key, entity.display_en_name, lang)
        st.session_state["_metrics_entity_url"] = signature

    if _DEBUG_FE:
        _debug_log_entity(entity, handler.get_transient_field_labels())

    rtl = is_rtl(lang)

    # ---- Entity header: name + Hebrew name ----
    name_display = entity.display_heb_name if rtl and entity.display_heb_name else entity.display_en_name
    alt_name = entity.display_en_name if rtl and entity.display_heb_name else entity.display_heb_name

    st.markdown(f"### {name_display}")
    if alt_name:
        st.caption(alt_name)

    if entity_tab == PAGE_PEOPLE:
        _render_family_tree_button(entity_key, lang)

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
    _render_relationship_fields(entity, transient_labels, lang, entity_key)


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
        text = (enum_text(badge["enum"], lang) if badge.get("enum")
                else badge.get("text") or get_text(badge.get("label_key") or "", lang))
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


def _toggle_relationship(field_name: str) -> None:
    selected = st.session_state.get("_entity_relationship_selected")
    st.session_state["_entity_relationship_selected"] = None if selected == field_name else field_name


@st.fragment
def _render_relationship_fields(entity, transient_labels: list, lang: str, entity_key: str) -> None:
    """Render populated relationship types in a collapsible navigation menu."""
    identity = (type(entity).__name__, entity_key)
    if st.session_state.get("_entity_relationship_identity") != identity:
        st.session_state["_entity_relationship_identity"] = identity
        st.session_state["_entity_relationship_selected"] = None

    fields_with_data = []
    for field_name, label_key in transient_labels:
        values = getattr(entity, field_name, None)
        if values and isinstance(values, list) and len(values) > 0:
            fields_with_data.append((field_name, label_key, values))

    if not fields_with_data:
        st.info(get_text("entity_search_ui.no_relationships", lang))
        return

    selected = st.session_state.get("_entity_relationship_selected")
    if selected not in {field_name for field_name, _, _ in fields_with_data}:
        selected = None
        st.session_state["_entity_relationship_selected"] = None

    st.markdown(f"#### {get_text('entity_search_ui.relationships', lang)}")
    with st.container(key="relationship_browser"):
        menu, detail = st.columns([1, 2], gap="medium")
        with menu:
            with st.container(key="relationship_menu"):
                for field_name, label_key, values in fields_with_data:
                    label = get_text(label_key, lang)
                    expanded = selected == field_name
                    st.button(
                        f"{'▾' if expanded else '▸'} {label} ({len(values)})",
                        key=f"relationship_menu_{field_name}",
                        type="primary" if expanded else "secondary",
                        use_container_width=True,
                        on_click=_toggle_relationship,
                        args=(field_name,),
                    )

        with detail:
            with st.container(border=True, key="relationship_detail"):
                if selected is None:
                    st.caption(get_text("entity_search_ui.choose_relationship", lang))
                else:
                    field_name, label_key, values = next(
                        field for field in fields_with_data if field[0] == selected
                    )
                    _render_relationship_list(
                        get_text(label_key, lang), values, field_name,
                        getattr(entity, "rel_links", {}) or {}, lang, entity,
                    )


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
    st.markdown(f"**{title} ({len(items)})**")
    for item in items:
        rel_keys = (getattr(entity, "rel_keys_by_field", {}) or {}).get(field_name, {}).get(item)
        link = rel_links.get(item)
        roles = (getattr(entity, "rel_roles", {}) or {}).get(link[0], []) if link else []
        display_name = ((getattr(entity, "rel_heb_names", {}) or {}).get(link[0]) or item
                        if is_rtl(lang) and link else item)
        if roles and is_rtl(lang):
            from backend.models_db.Enums import RoleType
            role_labels = [enum_text(RoleType(role), lang) if role in RoleType._value2member_map_ else role for role in roles]
        else:
            role_labels = [role.lower() for role in roles]
        display = f"{display_name} - {', '.join(role_labels)}" if role_labels else display_name
        _render_entity_item_popover(
            item, field_name, rel_links, lang,
            (getattr(entity, "display_heb_name", "") or getattr(entity, "display_en_name", ""))
            if is_rtl(lang) else getattr(entity, "display_en_name", ""),
            title, rel_keys, display,
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
    display_label: str | None = None,
) -> None:
    """Render a single related-entity name as a compact popover with two actions:
    view the entity, or view the sources of the relationship."""
    link_info = rel_links.get(item_name)  # (entity_key, EntityType) | None
    uid = f"{field_name}_{abs(hash(item_name))}"
    view_label = f"👁 {get_text('entity_search_ui.view_entity', lang)}"

    with st.popover(f"• {display_label or item_name}", use_container_width=True):
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

        st.link_button(
            f"📄 {get_text('entity_search_ui.view_sources', lang)}",
            page_url(PAGE_SOURCE_SEARCH, {
                PARAM_SOURCE_RELS: rel_keys,
                PARAM_SOURCE_REL_LABEL: f"{entity_name} · {rel_label} · {display_label or item_name}",
                PARAM_NAVIGATION_ORIGIN: "entity_relationship_sources",
                **admin_params(),
            }),
            key=f"relationship_sources_{uid}",
            use_container_width=True,
            disabled=not rel_keys,
        )


def _entity_type_to_tab(entity_type) -> str | None:
    """Map an EntityType to its navigation tab key, or None if not yet supported."""
    from backend.models_db.Enums import EntityType

    _TAB_MAP = {
        EntityType.EPerson: PAGE_PEOPLE,
        EntityType.EPlace: PAGE_PLACES,
        EntityType.ENation: PAGE_NATIONS,
        EntityType.ETribeOfIsrael: PAGE_TRIBES,
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

def _load_select_options(entity_tab: str, handler) -> list:
    """
    Load select options, caching in session state to avoid repeated DB calls.
    Cache is keyed by entity_tab. Clear by deleting the session key.
    """
    cache_key = f"_select_options_cache_{entity_tab}"
    if entity_tab == PAGE_SYMBOLS:
        cache_key += "_with_relationships"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = handler.get_select_options()
    return st.session_state[cache_key]
