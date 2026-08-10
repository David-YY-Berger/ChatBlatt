# bs"d - lehagdil torah velahadir
"""
Per-type facet renderers for the source-search panel.

Each public ``render_*_facet`` function is self-contained and may be called
individually from any page that needs a particular filter.
``render_facets_panel`` assembles all of them under a single Streamlit
sub-header and injects the required CSS once.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import streamlit as st

from backend.db.data_names.Books import Books
from backend.models_db.Enums import BookCategoryName, PassageType, SourceType
from system_common.Constants import (
    PAGE_NATIONS, PAGE_PEOPLE, PAGE_PLACES, PAGE_SYMBOLS, PAGE_TRIBES,
)

from .section import facet_section_header

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
    {"key": "number", "label": "Number", "entity_tab": None, "implemented": False},
    {"key": "animal", "label": "Animal", "entity_tab": None, "implemented": False},
    {"key": "food", "label": "Food", "entity_tab": None, "implemented": False},
    {"key": "plant", "label": "Plant", "entity_tab": None, "implemented": False},
    {"key": "symbol", "label": "Symbol", "entity_tab": PAGE_SYMBOLS, "implemented": True},
]

# ---------------------------------------------------------------------------
# CSS injection (loads from assets/facets.css – one call per page render)
# ---------------------------------------------------------------------------

_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


def inject_facet_css() -> None:
    """Inject the facet-panel CSS from ``assets/facets.css`` exactly once."""
    css_path = _ASSETS_DIR / "facets.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Book-grouping helpers
# ---------------------------------------------------------------------------

def _group_books_by_source_then_category() -> dict[SourceType, dict[BookCategoryName, list]]:
    """Return ``{SourceType: {BookCategoryName: [Book, ...]}}`` in sorted order."""
    result: dict[SourceType, dict[BookCategoryName, list]] = {}
    for b in Books.sorted_all():
        result.setdefault(b.source_type, {})
        result[b.source_type].setdefault(b.category, [])
        result[b.source_type][b.category].append(b)
    return result


# ---------------------------------------------------------------------------
# Individual facet renderers
# ---------------------------------------------------------------------------

def render_source_type_facet() -> None:
    """Checkbox filter for :class:`SourceType` values."""
    all_keys = [f"facet_src_type_{stype.name}" for stype in SourceType]
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if facet_section_header("📄 Source Type", "src_type", all_keys):
        for stype in SourceType:
            st.checkbox(stype.value, key=f"facet_src_type_{stype.name}", value=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_book_facet() -> None:
    """Three-level collapsible book filter: Source Type → Category → Book."""
    all_book_keys = [f"facet_book_{b.database_name}" for b in Books.sorted_all()]
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if facet_section_header("📚 Book", "book_all", all_book_keys):
        books_by_src = _group_books_by_source_then_category()
        for src_type, cats in books_by_src.items():
            src_book_keys = [
                f"facet_book_{b.database_name}"
                for cat_books in cats.values()
                for b in cat_books
            ]
            st.markdown('<div class="facet-section" style="margin-left:8px;margin-top:4px;">', unsafe_allow_html=True)
            if facet_section_header(f"📖 {src_type.value}", f"book_src_{src_type.name}", src_book_keys):
                for cat, cat_books in cats.items():
                    cat_keys = [f"facet_book_{b.database_name}" for b in cat_books]
                    st.markdown('<div class="facet-section" style="margin-left:16px;margin-top:4px;">', unsafe_allow_html=True)
                    if facet_section_header(cat.value, f"book_cat_{src_type.name}_{cat.name}", cat_keys):
                        for b in cat_books:
                            st.checkbox(
                                f"{b.en_display_name} ({b.heb_display_name})",
                                key=f"facet_book_{b.database_name}",
                                value=True,
                            )
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_passage_type_facet() -> None:
    """Checkbox filter for :class:`PassageType` values."""
    all_keys = [f"facet_passage_{p.name}" for p in PassageType]
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if facet_section_header("🔖 Passage Type", "passage_type", all_keys):
        for p in PassageType:
            st.checkbox(p.value, key=f"facet_passage_{p.name}", value=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_entity_facets() -> None:
    """Entity-type filter – a tab-style toggle row (one pill per entity type,
    fixed order) with a specific-entity picker panel for each active type.

    Modeled on the entity-type tab selector used on the Entity Search page:
    ``st.button`` with ``type="primary"`` when active / ``"secondary"`` when
    inactive. Unlike page navigation, several entity-type tabs may be active
    at once since this is a filter, not a page switch.
    """
    st.markdown('<div class="entity-panel">', unsafe_allow_html=True)
    st.markdown(
        "<div class='entity-panel-title'>🏷️ Filter by Entity</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="entity-tab-row">', unsafe_allow_html=True)
    cols = st.columns(len(ENTITY_TYPES))
    for col, ent in zip(cols, ENTITY_TYPES):
        active_key = f"entity_filter_active_{ent['key']}"
        is_active = st.session_state.get(active_key, False)
        with col:
            if st.button(
                ent["label"],
                key=f"entity_tab_btn_{ent['key']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state[active_key] = not is_active
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    active_entities = [
        ent for ent in ENTITY_TYPES
        if st.session_state.get(f"entity_filter_active_{ent['key']}", False)
    ]
    if active_entities:
        st.markdown('<div class="entity-select-panels">', unsafe_allow_html=True)
        for ent in active_entities:
            _render_entity_select_panel(ent)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_entity_select_panel(ent: dict) -> None:
    """Render the specific-entity picker panel for one active entity-type tab.

    Label sits to the left, with the combobox occupying the remaining space
    to its right (single row), instead of stacking label above combobox.
    """
    st.markdown('<div class="facet-section entity-select-section">', unsafe_allow_html=True)

    label_col, combo_col = st.columns([1, 4], vertical_alignment="center")
    with label_col:
        st.markdown(f"<div class='entity-select-label'>{ent['label']}</div>", unsafe_allow_html=True)

    with combo_col:
        if ent["implemented"]:
            options = _load_entity_select_options(ent["entity_tab"])
            if options:
                labels = [_format_entity_option_label(o) for o in options]
                st.multiselect(
                    f"Select {ent['label'].lower()}(s)",
                    options=labels,
                    key=f"entity_filter_selected_{ent['key']}",
                    label_visibility="collapsed",
                    placeholder=f"Search {ent['label'].lower()}s…",
                )
                # Selections are kept in session_state for now; wiring them
                # into the actual SourceSearchQuery is deferred (front-end
                # only task).
            else:
                st.caption("No entities found.")
        else:
            st.caption("Coming soon — this entity type isn't searchable yet.")

    st.markdown("</div>", unsafe_allow_html=True)


def _load_entity_select_options(entity_tab: str) -> list:
    """Fetch & cache (per Streamlit session) the select options for an
    entity-search tab, reusing the same handler registry as the Entity
    Search page."""
    cache_key = f"_entity_filter_options_cache_{entity_tab}"
    if cache_key not in st.session_state:
        from backend.app.controllers.entity_search.entity_search_controller import (
            get_entity_search_handler,
        )

        handler = get_entity_search_handler(entity_tab)
        st.session_state[cache_key] = handler.get_select_options() if handler else []
    return st.session_state[cache_key]


def _format_entity_option_label(opt) -> str:
    """Format an EntitySelectOption for display in the multiselect."""
    if opt.display_heb_name:
        return f"{opt.display_en_name} ({opt.display_heb_name})"
    return opt.display_en_name


# ---------------------------------------------------------------------------
# Top-level panel assembly
# ---------------------------------------------------------------------------

def render_facets_panel() -> None:
    """Render the left-column facets panel (source type, book, passage type).

    Entity facets are rendered separately at the top of the page via
    :func:`render_entity_facets`.  CSS injection is handled by the caller.
    """
    st.subheader("Facets")
    render_source_type_facet()
    render_book_facet()
    render_passage_type_facet()

