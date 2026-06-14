# bs"d - lehagdil torah velahadir

from __future__ import annotations

import streamlit as st
from collections import defaultdict

from translations1 import get_text, is_rtl

# Backend imports to populate facets and to call the search handler
from backend.models_db.Enums import SourceType, PassageType, BookCategoryName
from backend.db.data_names.Books import Books
from backend.app.SearchHandler import SearchHandler
from backend.app.SourceSearchQuery import SourceSearchQuery


def _group_books_by_category() -> dict[BookCategoryName, list]:
    grouped = defaultdict(list)
    for b in Books.sorted_all():
        grouped[b.category].append(b)
    return grouped


def render(lang: str) -> None:
    """Render the main search page with a centered free-text search and left-side facets.

    - Top center: text input labelled 'text similarity search' and button 'Find Sources'
    - Left: Facets (Source Type, Book grouped by BookCategory, Passage Type, Entities)
    Clicking Find Sources calls backend.app.SearchHandler.SearchHandler.get_answer_w_source_metadata
    with a SourceSearchQuery built from the text input and selected facets.
    """
    title = get_text("page_titles.search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    rtl = is_rtl(lang)

    # Layout: left facets narrow, main wide
    left_col, main_col = st.columns([2, 6])

    # --- Left: Facets ---
    with left_col:
        st.subheader("Facets")

        # Source Type
        st.markdown("**Source Type**")
        src_type_keys = []
        for stype in SourceType:
            key = f"facet_src_type_{stype.name}"
            checked = st.checkbox(f"{stype.value}", key=key, value=False)
            if checked:
                src_type_keys.append(stype)

        # Books grouped by category (preserve order via Books.sorted_all)
        st.markdown("**Book**")
        books_by_cat = _group_books_by_category()
        book_keys = []
        for cat in BookCategoryName:
            books = books_by_cat.get(cat, [])
            if not books:
                continue
            with st.expander(f"{cat.value}", expanded=False):
                for b in books:
                    key = f"facet_book_{b.database_name}"
                    checked = st.checkbox(f"{b.en_display_name} ({b.heb_display_name})", key=key, value=False)
                    if checked:
                        book_keys.append(b)

        # Passage Type
        st.markdown("**Passage Type**")
        passage_type_keys = []
        for p in PassageType:
            key = f"facet_passage_{p.name}"
            checked = st.checkbox(f"{p.value}", key=key, value=False)
            if checked:
                passage_type_keys.append(p)

        # Entity sections with a 'Select' button that opens a blank popup for now
        st.markdown("**Entities**")
        entities = [
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
        for ent_key, ent_label in entities:
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"{ent_label}")
            with cols[1]:
                if st.button("Select", key=f"select_ent_{ent_key}"):
                    # open blank popover/modal for now (placeholder)
                    with st.popover("Select entity", use_container_width=True):
                        st.write("")

    # --- Main: Search Bar and results area ---
    with main_col:
        st.markdown("<div style='display:flex; justify-content:center'>", unsafe_allow_html=True)
        query = st.text_input("text similarity search", key="free_text_query")
        st.markdown("</div>", unsafe_allow_html=True)

        # Find Sources button
        if st.button("Find Sources"):
            # Build SourceSearchQuery from selected facets
            free_text = st.session_state.get("free_text_query", "")
            max_sources = 50

            # Re-read selected enums from session state (checkbox keys)
            selected_src_types = []
            for stype in SourceType:
                key = f"facet_src_type_{stype.name}"
                if st.session_state.get(key, False):
                    selected_src_types.append(stype)

            selected_passage_types = []
            for p in PassageType:
                key = f"facet_passage_{p.name}"
                if st.session_state.get(key, False):
                    selected_passage_types.append(p)

            # Note: Book filtering is handled server-side by SearchHandler.filter_by_book.
            selected_books = []
            for b in Books.sorted_all():
                key = f"facet_book_{b.database_name}"
                if st.session_state.get(key, False):
                    selected_books.append(b)

            # For now we don't include entity or rel ids (popup to be implemented later)
            query_obj = SourceSearchQuery(
                free_text_similarity=free_text,
                max_sources=max_sources,
                src_types=selected_src_types,
                passage_types=selected_passage_types,
                entity_ids=[],
                rel_ids=[],
            )

            handler = SearchHandler()
            with st.spinner("Searching..."):
                try:
                    ans = handler.get_answer_w_source_metadata(query_obj)
                except Exception as e:
                    st.error(f"Search failed: {e}")
                    return

            st.success(f"Found {len(ans.src_metadata_lst)} sources (metadata only)")
            for src in ans.src_metadata_lst[:20]:
                st.markdown(f"- **{src.key}** — {getattr(src, 'summary_en', '')}")

