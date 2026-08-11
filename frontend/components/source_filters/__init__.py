# bs"d - lehagdil torah velahadir
"""
``components.source_filters`` – self-contained left-hand source-filter widget.

Two independent filters are exposed:

  1. **Passage Type** – a flat, always-visible checkbox list.
  2. **Sources** – a collapsed-by-default, truly nested tree:
     Source Type -> Book Category -> Book.

This package is deliberately self-contained (its own CSS, its own
session-state keys) so it can be dropped onto any page, not just the
source-search page. Typical usage::

    from components.source_filters import (
        inject_source_filters_css,
        render_source_filters,
        render_active_filter_chips,
    )

    inject_source_filters_css()          # once per page
    render_source_filters()              # in the left column
    render_active_filter_chips()         # directly above the results

If a page ever needs two independent instances of the filter side by side,
pass a distinct ``namespace`` string to every call so their session-state
keys don't collide.
"""

from .chips import render_active_filter_chips
from .render import (
    inject_source_filters_css,
    render_passage_type_section,
    render_source_filters,
    render_sources_section,
)
from .state import (
    DEFAULT_NAMESPACE,
    get_selected_books,
    get_selected_passage_types,
    get_selected_source_types,
)

__all__ = [
    # Panel
    "render_source_filters",
    "inject_source_filters_css",
    # Individual sections (in case a page only wants one of them)
    "render_passage_type_section",
    "render_sources_section",
    # Active filter chips (render above the results)
    "render_active_filter_chips",
    # Selection getters – read the current filter state from any page
    "get_selected_passage_types",
    "get_selected_books",
    "get_selected_source_types",
    "DEFAULT_NAMESPACE",
]
