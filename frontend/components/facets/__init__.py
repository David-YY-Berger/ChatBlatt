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
    ENTITY_OPTIONS,
    inject_facet_css,
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
    # Generic section widget (reusable on any page)
    "facet_section_header",
    # Constants
    "ENTITY_OPTIONS",
]

