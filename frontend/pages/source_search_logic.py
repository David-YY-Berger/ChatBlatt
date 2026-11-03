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
from components.facets import get_selected_entity_ids
from components.source_filters import get_selected_book_names, get_selected_passage_types
from system_common.SystemFunctions import get_ts_datetime

logger = logging.getLogger(__name__)


REL_SEARCH_KEY = "_source_search_rel"
REL_SEARCH_PENDING_KEY = "_source_search_rel_pending"


def set_relationship_search(rel_ids: list[str], label: str) -> None:
    """Pre-set the source-search page to look for sources of the given
    relationships (Rel keys); the page runs the search on its next render."""
    st.session_state[REL_SEARCH_KEY] = {"rel_ids": list(rel_ids), "label": label}
    st.session_state[REL_SEARCH_PENDING_KEY] = True
    st.session_state.pop("_search_ans", None)
    st.session_state.pop("_search_error", None)


def get_relationship_search() -> dict | None:
    return st.session_state.get(REL_SEARCH_KEY)


def clear_relationship_search() -> None:
    st.session_state.pop(REL_SEARCH_KEY, None)
    st.session_state.pop(REL_SEARCH_PENDING_KEY, None)


def collect_search_query() -> SourceSearchQuery:
    """Read the current source-filters selections and free-text box to build
    a :class:`SourceSearchQuery`."""
    free_text = st.session_state.get("free_text_query", "")

    selected_passage_types = get_selected_passage_types()
    rel_search = get_relationship_search()

    return SourceSearchQuery(
        free_text_similarity=free_text,
        max_sources=50,
        passage_types=selected_passage_types,
        book_names=get_selected_book_names(),
        entity_ids=get_selected_entity_ids(),
        rel_ids=rel_search["rel_ids"] if rel_search else [],
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

