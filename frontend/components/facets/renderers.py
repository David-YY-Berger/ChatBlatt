# bs"d - lehagdil torah velahadir
"""
Entity-type facet renderer for the source-search panel.

Note: the Passage Type and Source Type filters live in `components.source_filters`;
this module only deals with the entity-type picker panel.
"""

from __future__ import annotations

import concurrent.futures
import logging
from pathlib import Path

import streamlit as st
from translations1 import get_text
from components.entity_option_labels import unique_entity_option_labels

from system_common.Constants import (
    PAGE_ANIMALS, PAGE_FOODS, PAGE_NATIONS, PAGE_NUMBERS, PAGE_PEOPLE,
    PAGE_PLACES, PAGE_PLANTS, PAGE_SYMBOLS, PAGE_TRIBES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entities known to the facet filter
#
# ``entity_tab`` maps to the entity-search handler registry key (see
# ``backend.app.controllers.entity_search.entity_search_controller``) for
# types that already support real entity lookup; ``None`` for types that
# don't have a search handler yet (front-end placeholder only).
#
# Order is fixed per product requirement (not alphabetical).
# ---------------------------------------------------------------------------

ENTITY_TYPES: list[dict] = [
    {"key": "person", "label": "Person", "entity_tab": PAGE_PEOPLE, "implemented": True},
    {"key": "place", "label": "Place", "entity_tab": PAGE_PLACES, "implemented": True},
    {"key": "tribe_of_israel", "label": "Tribe Of Israel", "entity_tab": PAGE_TRIBES, "implemented": True},
    {"key": "nation", "label": "Nation", "entity_tab": PAGE_NATIONS, "implemented": True},
    {"key": "number", "label": "Number", "entity_tab": PAGE_NUMBERS, "implemented": True},
    {"key": "animal", "label": "Animal", "entity_tab": PAGE_ANIMALS, "implemented": True},
    {"key": "food", "label": "Food", "entity_tab": PAGE_FOODS, "implemented": True},
    {"key": "plant", "label": "Plant", "entity_tab": PAGE_PLANTS, "implemented": True},
    {"key": "symbol", "label": "Symbol", "entity_tab": PAGE_SYMBOLS, "implemented": True},
]

_VISIBLE_ENTITY_TYPES = [ent for ent in ENTITY_TYPES if ent["key"] != "symbol"]

# ---------------------------------------------------------------------------
# Background preloading of entity select-options
#
# Fetching each visible entity type's select options is a DB round-trip.
# Previously this happened lazily the first time a user clicked an
# entity-type tab, which meant a visible stall on that click. Instead, we
# kick off all visible-type fetches in parallel as soon as the page renders, and
# resolve/cache the results the first time they're actually needed. Because
# the fetches start well before the user clicks anything, by the time a tab
# is activated the data is normally already sitting in the cache — so
# rendering the panel is just a session_state lookup, no DB latency.
#
# The executor is a module-level singleton so it's shared across Streamlit
# sessions/reruns rather than re-created on every script run.
# ---------------------------------------------------------------------------

_ENTITY_OPTIONS_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="entity-options-preload",
)


def _entity_options_cache_key(entity_tab: str) -> str:
    return f"_entity_filter_options_cache_{entity_tab}"


def _fetch_entity_options(entity_tab: str) -> list:
    """Blocking DB fetch of select options for one entity tab (runs on a
    background thread, or synchronously as a fallback)."""
    from backend.app.controllers.entity_search.entity_search_controller import (
        get_entity_search_handler,
    )

    handler = get_entity_search_handler(entity_tab)
    return handler.get_select_options() if handler else []


def preload_all_entity_options() -> None:
    """Kick off background fetches for visible entity types' select options,
    without blocking page rendering.

    Safe to call on every rerun: it only submits work once per session
    (guarded by a session_state flag), so subsequent calls are no-ops.
    """
    if st.session_state.get("_entity_options_preload_started"):
        return
    st.session_state["_entity_options_preload_started"] = True

    for ent in _VISIBLE_ENTITY_TYPES:
        if not ent["implemented"]:
            continue
        entity_tab = ent["entity_tab"]
        if _entity_options_cache_key(entity_tab) in st.session_state:
            continue
        future_key = f"_entity_options_future_{entity_tab}"
        if future_key in st.session_state:
            continue
        st.session_state[future_key] = _ENTITY_OPTIONS_EXECUTOR.submit(
            _fetch_entity_options, entity_tab,
        )

# ---------------------------------------------------------------------------
# CSS injection (loads from assets/facets.css – one call per page render)
# ---------------------------------------------------------------------------

_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


def inject_facet_css() -> None:
    """Inject the facet-panel CSS from ``assets/facets.css`` exactly once."""
    css_path = _ASSETS_DIR / "facets.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_entity_facets(lang: str = "en") -> None:
    """Entity-type filter – a specific-entity picker panel for each visible
    type, always shown (no tab toggles). Types without a search handler yet
    show a "coming soon" placeholder instead of a picker.
    """
    # Fire off background fetches for all entity lists up front (no-op after
    # the first call this session) so rendering below never has to wait
    # on a DB round-trip.
    preload_all_entity_options()

    st.markdown('<div class="entity-panel">', unsafe_allow_html=True)
    st.markdown(
        f"<div class='entity-panel-title'>🏷️ {get_text('source_search_ui.filter_by_entity', lang)}</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="entity-select-panels">', unsafe_allow_html=True)
    for ent in _VISIBLE_ENTITY_TYPES:
        _render_entity_select_panel(ent, lang)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


@st.fragment
def _render_entity_select_panel(ent: dict, lang: str = "en") -> None:
    """Render the specific-entity picker panel for one active entity-type tab.

    Label sits to the left, with the combobox occupying the remaining space
    to its right (single row), instead of stacking label above combobox.
    """
    st.markdown('<div class="facet-section entity-select-section">', unsafe_allow_html=True)

    label = get_text(f"facet_entities.{ent['key']}", lang)
    label_col, combo_col = st.columns([1, 4], vertical_alignment="center")
    with label_col:
        st.markdown(f"<div class='entity-select-label'>{label}</div>", unsafe_allow_html=True)

    with combo_col:
        if ent["implemented"]:
            options = _load_entity_select_options(ent["entity_tab"])
            if options:
                labels = _unique_option_labels(options)
                display_labels = dict(zip(labels, _unique_option_labels(options, lang)))
                st.multiselect(
                    get_text("source_search_ui.select_entities", lang).format(entity=label),
                    options=labels,
                    format_func=lambda value: display_labels[value],
                    key=f"entity_filter_selected_{ent['key']}",
                    label_visibility="collapsed",
                    placeholder=get_text("source_search_ui.search_entities", lang).format(entity=label),
                )
                # Selections live in session_state under this widget's key;
                # get_selected_entity_ids() resolves them (across every
                # entity-type panel) back to entity keys for the query.
            else:
                st.caption(get_text("source_search_ui.no_entities", lang))
        else:
            st.caption(get_text("source_search_ui.entity_unavailable", lang))

    st.markdown("</div>", unsafe_allow_html=True)


def _load_entity_select_options(entity_tab: str) -> list:
    """Return the (already-preloading) select options for an entity-search
    tab, resolving the background future started in
    :func:`preload_all_entity_options` on first access.

    Normally a plain session_state cache hit — the background fetch,
    started when the page first rendered, has already completed by the
    time a user activates a tab. If it hasn't (e.g. a very fast click),
    this blocks only long enough for that one fetch to finish, instead of
    the old behavior of starting the DB call at click time.
    """
    cache_key = _entity_options_cache_key(entity_tab)
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    future_key = f"_entity_options_future_{entity_tab}"
    future = st.session_state.pop(future_key, None)
    try:
        options = future.result() if future is not None else _fetch_entity_options(entity_tab)
    except Exception:
        logger.exception("Failed to load entity select options for %s", entity_tab)
        options = []

    st.session_state[cache_key] = options
    return options


def _unique_option_labels(options: list, lang: str = "en") -> list[str]:
    """Display labels aligned with `options`; labels shared by several options
    (e.g. two people with the same name and roles) get a short key suffix so each
    stays individually selectable."""
    return unique_entity_option_labels(options, lang)


def get_selected_entity_ids() -> list[str]:
    """Flatten every entity-type panel's current multiselect selections into
    a single list of entity keys, for use as ``SourceSearchQuery.entity_ids``.

    Each panel's multiselect stores selected *display labels* (not keys) in
    ``st.session_state[f"entity_filter_selected_{ent['key']}"]``; this
    resolves each label back to its key(s) using that entity type's
    (already-loaded/cached) select options.

    Some option types (e.g. ``NumberSelectOption``) group several underlying
    entities under a single displayed label — e.g. many ENumber entities can
    share ``display_en_name == "7"``. For those, ``entity_keys`` carries every
    underlying entity key that shares the label, and *all* of them must be
    included so the search matches any source referencing any of them, not
    just the first one chosen as the option's ``key``.
    """
    entity_ids: list[str] = []
    for ent in ENTITY_TYPES:
        if not ent["implemented"]:
            continue
        selected_labels = st.session_state.get(f"entity_filter_selected_{ent['key']}")
        if not selected_labels:
            continue
        options = _load_entity_select_options(ent["entity_tab"])
        label_to_keys = {
            label: (getattr(o, "entity_keys", None) or [o.key])
            for label, o in zip(_unique_option_labels(options), options)
        }
        for label in selected_labels:
            if label in label_to_keys:
                entity_ids.extend(label_to_keys[label])
    return entity_ids



def get_selected_entity_option_keys() -> list[str]:
    """The selected select-option keys (one per picked label) across all entity-type
    panels - the compact form used in shareable URLs."""
    keys: list[str] = []
    for ent in ENTITY_TYPES:
        if not ent["implemented"]:
            continue
        selected_labels = st.session_state.get(f"entity_filter_selected_{ent['key']}")
        if not selected_labels:
            continue
        opts = _load_entity_select_options(ent["entity_tab"])
        label_to_key = {label: o.key for label, o in zip(_unique_option_labels(opts), opts)}
        keys.extend(label_to_key[l] for l in selected_labels if l in label_to_key)
    return keys


def get_selected_entity_names() -> list[str]:
    """Return the English names of the selected entities, in selection order."""
    names: list[str] = []
    for ent in ENTITY_TYPES:
        if not ent["implemented"]:
            continue
        selected_labels = st.session_state.get(f"entity_filter_selected_{ent['key']}")
        if not selected_labels:
            continue
        options = _load_entity_select_options(ent["entity_tab"])
        label_to_name = {
            label: option.display_en_name
            for label, option in zip(_unique_option_labels(options), options)
        }
        names.extend(label_to_name[label] for label in selected_labels if label in label_to_name)
    return list(dict.fromkeys(names))


def get_selected_entity_metrics() -> list[tuple[str, str, str]]:
    """Selected option type, key and canonical English name, in panel order."""
    selected = []
    for ent in ENTITY_TYPES:
        labels = st.session_state.get(f"entity_filter_selected_{ent['key']}")
        if not ent["implemented"] or not labels:
            continue
        options = _load_entity_select_options(ent["entity_tab"])
        by_label = dict(zip(_unique_option_labels(options), options))
        for label in labels:
            if label in by_label:
                option = by_label[label]
                selected.append((ent["key"], option.key, option.display_en_name))
    return selected


def set_selected_entity_option_keys(keys: list[str]) -> None:
    """Pre-select the panels' multiselects from option keys. Must run before the
    panels render in the current script run."""
    wanted = set(keys)
    for ent in ENTITY_TYPES:
        if not ent["implemented"]:
            continue
        options = _load_entity_select_options(ent["entity_tab"])
        st.session_state[f"entity_filter_selected_{ent['key']}"] = [
            label for label, o in zip(_unique_option_labels(options), options) if o.key in wanted
        ]
