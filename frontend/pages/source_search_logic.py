# bs"d - lehagdil torah velahadir
"""
Search logic for the source-search page.

Kept separate from the UI layer so it can be unit-tested independently and
reused if other pages need the same query/result model.
"""

from __future__ import annotations

import logging
import streamlit as st

from backend.app.SourceSearchHandler import SourceSearchHandler
from backend.app.SourceSearchQuery import SourceSearchQuery
from components.source_filters import get_selected_books, get_selected_passage_types
from system_common.SystemFunctions import get_ts_datetime

logger = logging.getLogger(__name__)


def collect_search_query() -> SourceSearchQuery:
    """Read the current source-filters selections and free-text box to build
    a :class:`SourceSearchQuery`."""
    free_text = st.session_state.get("free_text_query", "")

    selected_passage_types = get_selected_passage_types()
    # Book-level selection – captured for the future; not yet wired into
    # server-side filtering (backend support is out of scope for now).
    selected_books = get_selected_books()  # noqa: F841
    selected_src_types = sorted(
        {b.source_type for b in selected_books}, key=lambda st_: st_.value,
    )

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
    handler = SourceSearchHandler()
    time_begin = get_ts_datetime()
    logger.info("Starting search with SearchHandler.get_full_answer. search start time: %s", time_begin)

    with st.spinner("Searching..."):
        ans = handler.get_full_answer(query_obj)

    elapsed = str(get_ts_datetime() - time_begin)
    found_count = len(getattr(ans, "src_metadata_lst", []))
    logger.info("Search completed. Found %d sources. total search time: %s", found_count, elapsed)
    return ans, elapsed

