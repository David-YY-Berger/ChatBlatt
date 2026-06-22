# bs"d - lehagdil torah velahadir
"""
Search logic for the source-search page.

Kept separate from the UI layer so it can be unit-tested independently and
reused if other pages need the same query/result model.
"""

from __future__ import annotations

import logging
import streamlit as st

from backend.app.SearchHandler import SearchHandler
from backend.app.SourceSearchQuery import SourceSearchQuery
from backend.db.data_names.Books import Books
from backend.models_db.Enums import PassageType, SourceType
from system_common.SystemFunctions import get_ts_datetime

logger = logging.getLogger(__name__)


def collect_search_query() -> SourceSearchQuery:
    """Read current session-state checkbox values and build a :class:`SourceSearchQuery`."""
    free_text = st.session_state.get("free_text_query", "")

    selected_src_types = [
        stype for stype in SourceType
        if st.session_state.get(f"facet_src_type_{stype.name}", False)
    ]
    selected_passage_types = [
        p for p in PassageType
        if st.session_state.get(f"facet_passage_{p.name}", False)
    ]
    # Book selection – passed to SearchHandler for server-side filtering.
    selected_books = [  # noqa: F841
        b for b in Books.sorted_all()
        if st.session_state.get(f"facet_book_{b.database_name}", False)
    ]

    return SourceSearchQuery(
        free_text_similarity=free_text,
        max_sources=50,
        src_types=selected_src_types,
        passage_types=selected_passage_types,
        entity_ids=[],
        rel_ids=[],
    )


def run_search(query_obj: SourceSearchQuery):
    """Execute the search and return ``(answer, elapsed_str)``."""
    handler = SearchHandler()
    time_begin = get_ts_datetime()
    logger.info("Starting search with SearchHandler.get_full_answer. search start time: %s", time_begin)

    with st.spinner("Searching..."):
        ans = handler.get_full_answer(query_obj)

    elapsed = str(get_ts_datetime() - time_begin)
    found_count = len(getattr(ans, "src_metadata_lst", []))
    logger.info("Search completed. Found %d sources. total search time: %s", found_count, elapsed)
    return ans, elapsed

