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

from .section import facet_section_header

# ---------------------------------------------------------------------------
# Entities known to the facet filter
# ---------------------------------------------------------------------------

ENTITY_OPTIONS: list[tuple[str, str]] = [
    ("Animal", "Animal"),
    ("Food", "Food"),
    ("Nation", "Nation"),
    ("Number", "Number"),
    ("Person", "Person"),
    ("Place", "Place"),
    ("Plant", "Plant"),
    ("Symbol", "Symbol"),
    ("TribeOfIsrael", "Tribe Of Israel"),
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
            st.checkbox(stype.value, key=f"facet_src_type_{stype.name}", value=False)
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
                                value=False,
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
            st.checkbox(p.value, key=f"facet_passage_{p.name}", value=False)
    st.markdown("</div>", unsafe_allow_html=True)


def render_entity_facets() -> None:
    """Entity-type filter (expand-to-pick pattern, future: entity selector popover)."""
    st.markdown('<div class="facet-section">', unsafe_allow_html=True)
    if facet_section_header("🏷️ Entities", "entities"):
        for ent_key, ent_label in ENTITY_OPTIONS:
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(ent_label)
            with cols[1]:
                if st.button("Select", key=f"select_ent_{ent_key}"):
                    with st.popover("Select entity", use_container_width=True):
                        st.write("")
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Top-level panel assembly
# ---------------------------------------------------------------------------

def render_facets_panel() -> None:
    """Render the complete facets sidebar panel (CSS + all facet groups)."""
    inject_facet_css()
    st.subheader("Facets")
    render_source_type_facet()
    render_book_facet()
    render_passage_type_facet()
    render_entity_facets()

