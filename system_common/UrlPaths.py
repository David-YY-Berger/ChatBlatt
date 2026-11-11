# bs"d - lehagdil torah velahadir
"""
Single source of truth for the web app's URL paths and query-parameter names.

Lives in ``system_common`` (importable by both ``frontend`` and ``backend``).
Nothing here touches the file system - for file/dir paths see ``backend/common/Paths.py``.

Streamlit limitation: a page's ``url_path`` cannot contain ``/``, so what would
naturally be ``/entity_search/people`` is the flat path ``/entity_search_people``.
"""

from __future__ import annotations

import os
from urllib.parse import urlencode

from system_common.Constants import (
    PAGE_ABOUT, PAGE_ENTITY_SEARCH, PAGE_FAMILY_TREE, PAGE_HOME, PAGE_NATIONS,
    PAGE_NUMBER_SEARCH, PAGE_PEOPLE, PAGE_PLACES, PAGE_SOURCE_SEARCH,
    PAGE_STUDIED_FROM, PAGE_SYMBOLS, PAGE_TREES, PAGE_TRIBES,
)

BASE_URL = os.environ.get("EITZ_HABINA_BASE_URL", "https://eitz-habina.fly.dev/")
PARAM_ADMIN = "admin"
PARAM_NAVIGATION_ORIGIN = "via"

# page key -> url_path ("" = the default/landing page)
URL_PATHS: dict[str, str] = {
    PAGE_HOME: "",
    PAGE_ABOUT: "about",
    PAGE_SOURCE_SEARCH: "source_search",
    PAGE_NUMBER_SEARCH: "number_search",
    PAGE_ENTITY_SEARCH: "entity_search",
    PAGE_PEOPLE: "entity_search_people",
    PAGE_PLACES: "entity_search_places",
    PAGE_NATIONS: "entity_search_nations",
    PAGE_TRIBES: "entity_search_tribes",
    PAGE_SYMBOLS: "entity_search_symbols",
    PAGE_TREES: "trees",
    PAGE_FAMILY_TREE: "trees_genealogy_tree",
    PAGE_STUDIED_FROM: "trees_studied_from_tree",
}

# ---- Source search params (list values are comma-separated) ----
PARAM_SOURCE_TEXT = "q"               # free-text similarity query
PARAM_SOURCE_PASSAGE_TYPES = "pt"     # PassageType names
PARAM_SOURCE_TYPES = "st"             # SourceType names
PARAM_SOURCE_ENTITIES = "ent"         # entity select-option keys
PARAM_SOURCE_RELS = "rel"             # Rel keys (relationship search)
PARAM_SOURCE_REL_LABEL = "rel_label"  # display label of the relationship search

# ---- Number search params ----
PARAM_NUMBER_TYPE = "type"            # NUMBER_SEARCH_TYPE_NUMBER | NUMBER_SEARCH_TYPE_UNIT
PARAM_NUMBER_VALUE = "value"
NUMBER_SEARCH_TYPE_NUMBER = "number"
NUMBER_SEARCH_TYPE_UNIT = "unit"

# ---- Entity search param (on each entity_search_<type> page) ----
PARAM_ENTITY_ID = "id"

LIST_SEPARATOR = ","


def page_url(page_key: str, params: dict | None = None, base_url: str = BASE_URL) -> str:
    """Absolute URL of a page, with optional query params (lists are comma-joined,
    empty values dropped)."""
    flat = {}
    for k, v in (params or {}).items():
        if isinstance(v, (list, tuple, set)):
            v = LIST_SEPARATOR.join(str(x) for x in v)
        if v not in (None, ""):
            flat[k] = v
    url = base_url.rstrip("/") + "/" + URL_PATHS[page_key]
    return f"{url}?{urlencode(flat)}" if flat else url


def split_list(value: str | None) -> list[str]:
    return [x for x in (value or "").split(LIST_SEPARATOR) if x]
