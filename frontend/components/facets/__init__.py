# bs"d - lehagdil torah velahadir
"""
``components.facets`` – entity-type filter panel (the always-visible
per-entity picker shown above the search box).

Note: the Passage Type and Source Type filters live in `components.source_filters`.
"""

from .renderers import (
    ENTITY_TYPES,
    get_selected_entity_ids,
    get_selected_entity_names,
    get_selected_entity_option_keys,
    set_selected_entity_option_keys,
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
    "get_selected_entity_names",
    "get_selected_entity_option_keys",
    "set_selected_entity_option_keys",
    # Constants
    "ENTITY_TYPES",
]
