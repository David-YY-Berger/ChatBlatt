# bs"d - lehagdil torah velahadir
"""Page registry + helper for navigating between pages (optionally with URL params)."""

from __future__ import annotations

import streamlit as st

_PAGES: dict[str, st.Page] = {}


def register_pages(pages: dict[str, st.Page]) -> None:
    _PAGES.clear()
    _PAGES.update(pages)


def go(page_key: str, **params) -> None:
    """Switch to a page, replacing the URL query params with ``params`` (lists are comma-joined)."""
    from system_common.UrlPaths import LIST_SEPARATOR, PARAM_ADMIN
    from metrics import admin_params

    flat = admin_params()
    for k, v in params.items():
        if k == PARAM_ADMIN and PARAM_ADMIN in flat:
            continue
        if isinstance(v, (list, tuple, set)):
            v = LIST_SEPARATOR.join(str(x) for x in v)
        if v not in (None, ""):
            flat[k] = str(v)
    st.switch_page(_PAGES[page_key], query_params=flat)
