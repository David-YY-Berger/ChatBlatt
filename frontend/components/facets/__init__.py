# bs"d - lehagdil torah velahadir
"""
``components.facets`` – entity-type filter panel (the always-visible
per-entity picker shown above the search box).

Note: the source-type/book-category/book and passage-type left-hand
filters have moved to ``components.source_filters`` – a standalone,
reusable component. Import from there instead::

    from components.source_filters import render_source_filters
"""

from .renderers import (
    ENTITY_TYPES,
    get_selected_entity_ids,
    inject_facet_css,
    preload_all_entity_options,
    render_entity_facets,
)

__all__ = [
    "render_entity_facets",
    "inject_facet_css",
    # Background preloading (call early on page load if you need the lists
    # ready before render_entity_facets runs, e.g. to preload while other
    # parts of the page render)
    "preload_all_entity_options",
    # Read the entity-type panels' current selections (as entity keys), for
    # building a SourceSearchQuery.
    "get_selected_entity_ids",
    # Constants
    "ENTITY_TYPES",
]

