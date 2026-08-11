# bs"d - lehagdil torah velahadir
"""
``components.facets`` – public API for the facet-panel subsystem.

Typical usage::

    from components.facets import render_facets_panel
    render_facets_panel()

Lower-level helpers are importable directly from their submodules when needed
by other pages::

    from components.facets.section import facet_section_header
    from components.facets.renderers import render_book_facet
"""

from .renderers import (
    ENTITY_TYPES,
    inject_facet_css,
    preload_all_entity_options,
    render_book_facet,
    render_entity_facets,
    render_facets_panel,
    render_passage_type_facet,
    render_source_type_facet,
)
from .section import facet_section_header

__all__ = [
    # Panel
    "render_facets_panel",
    "inject_facet_css",
    # Individual facet renderers
    "render_source_type_facet",
    "render_book_facet",
    "render_passage_type_facet",
    "render_entity_facets",
    # Background preloading (call early on page load if you need the lists
    # ready before render_entity_facets runs, e.g. to preload while other
    # parts of the page render)
    "preload_all_entity_options",
    # Generic section widget (reusable on any page)
    "facet_section_header",
    # Constants
    "ENTITY_TYPES",
]

