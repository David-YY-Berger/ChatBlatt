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
from components.facets import (
    get_selected_entity_ids,
    get_selected_entity_option_keys,
    set_selected_entity_option_keys,
)
from components.source_filters import (
    get_selected_book_names,
    get_selected_passage_type_names,
    get_selected_passage_types,
    set_selected_filters,
)
from system_common.Constants import PAGE_SOURCE_SEARCH
from system_common.UrlPaths import (
    LIST_SEPARATOR, PARAM_SOURCE_BOOKS, PARAM_SOURCE_ENTITIES, PARAM_SOURCE_PASSAGE_TYPES,
    PARAM_SOURCE_REL_LABEL, PARAM_SOURCE_RELS, PARAM_SOURCE_TEXT, page_url, split_list,
)

from system_common.SystemFunctions import get_ts_datetime

logger = logging.getLogger(__name__)


REL_SEARCH_KEY = "_source_search_rel"
URL_SIG_KEY = "_source_search_url_sig"


def set_relationship_search(rel_ids: list[str], label: str) -> None:
    st.session_state[REL_SEARCH_KEY] = {"rel_ids": list(rel_ids), "label": label}


def get_relationship_search() -> dict | None:
    return st.session_state.get(REL_SEARCH_KEY)


def clear_relationship_search() -> None:
    st.session_state.pop(REL_SEARCH_KEY, None)


def current_url_params() -> dict:
    """The current search form as URL params (see ``system_common.UrlPaths``)."""
    rel_search = get_relationship_search()
    return {
        PARAM_SOURCE_TEXT: st.session_state.get("free_text_query", "").strip(),
        PARAM_SOURCE_PASSAGE_TYPES: get_selected_passage_type_names(),
        PARAM_SOURCE_BOOKS: get_selected_book_names(),
        PARAM_SOURCE_ENTITIES: get_selected_entity_option_keys(),
        PARAM_SOURCE_RELS: rel_search["rel_ids"] if rel_search else [],
        PARAM_SOURCE_REL_LABEL: rel_search["label"] if rel_search else "",
    }


def flat_url_params() -> dict[str, str]:
    """``current_url_params`` as ``{name: str}`` with empty params dropped."""
    out = {}
    for k, v in current_url_params().items():
        v = LIST_SEPARATOR.join(v) if isinstance(v, list) else v
        if v:
            out[k] = v
    return out


def current_search_url() -> str:
    return page_url(PAGE_SOURCE_SEARCH, flat_url_params())


def sync_url_with_search() -> None:
    """Make the browser URL reflect the executed search, so it can be shared."""
    params = flat_url_params()
    st.query_params.from_dict(params)
    st.session_state[URL_SIG_KEY] = tuple(sorted(params.items()))


def apply_url_params() -> bool:
    """If the URL carries a search not yet applied this session, load it into the
    form widgets (call before they render). Returns True when a search should run."""
    params = {k: v for k, v in st.query_params.items() if v}
    known = {PARAM_SOURCE_TEXT, PARAM_SOURCE_PASSAGE_TYPES, PARAM_SOURCE_BOOKS,
             PARAM_SOURCE_ENTITIES, PARAM_SOURCE_RELS, PARAM_SOURCE_REL_LABEL}
    params = {k: v for k, v in params.items() if k in known}
    if not params or st.session_state.get(URL_SIG_KEY) == tuple(sorted(params.items())):
        return False
    st.session_state[URL_SIG_KEY] = tuple(sorted(params.items()))

    st.session_state["free_text_query"] = params.get(PARAM_SOURCE_TEXT, "")
    set_selected_filters(split_list(params.get(PARAM_SOURCE_PASSAGE_TYPES)),
                         split_list(params.get(PARAM_SOURCE_BOOKS)))
    set_selected_entity_option_keys(split_list(params.get(PARAM_SOURCE_ENTITIES)))
    rels = split_list(params.get(PARAM_SOURCE_RELS))
    if rels:
        set_relationship_search(rels, params.get(PARAM_SOURCE_REL_LABEL, ""))
    else:
        clear_relationship_search()
    return True


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

