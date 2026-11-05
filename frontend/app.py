# bs"d - lehagdil torah velahadir

from __future__ import annotations

import sys
from pathlib import Path

# Add frontend directory to path for imports
FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

# Add project root to path so 'backend' package is importable
PROJECT_ROOT = FRONTEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

import navigation
from components.header import render_header
from components.layout import apply_layout, language_selector
from translations1 import get_text
from pages import about, entity_search, home, number_search, source_search, trees
from system_common.Constants import (
    DEFAULT_LANG,
    PAGE_HOME, PAGE_ABOUT, PAGE_NUMBER_SEARCH, PAGE_SOURCE_SEARCH,
    PAGE_ENTITY_SEARCH, PAGE_TREES,
    PAGE_PEOPLE, PAGE_PLACES, PAGE_NATIONS, PAGE_TRIBES, PAGE_SYMBOLS,
    PAGE_GENOLOGY, PAGE_STUDIED_FROM,
)
from system_common.UrlPaths import URL_PATHS

import logging

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

ENTITY_PAGES = (PAGE_PEOPLE, PAGE_PLACES, PAGE_NATIONS, PAGE_TRIBES, PAGE_SYMBOLS)
TREE_PAGES = (PAGE_GENOLOGY, PAGE_STUDIED_FROM)


def _init_state() -> None:
    if "lang" not in st.session_state:
        st.session_state["lang"] = DEFAULT_LANG


def _renderer(page_key: str):
    """The function that renders `page_key`, called with the current language."""
    if page_key == PAGE_HOME:
        return home.render
    if page_key == PAGE_ABOUT:
        return about.render
    if page_key == PAGE_NUMBER_SEARCH:
        return number_search.render
    if page_key == PAGE_SOURCE_SEARCH:
        return source_search.render
    if page_key == PAGE_ENTITY_SEARCH:
        return entity_search.render
    if page_key in ENTITY_PAGES:
        return lambda lang: entity_search.render(lang, selected=page_key)
    if page_key == PAGE_TREES:
        return trees.render
    return lambda lang: trees.render(lang, selected=page_key)


def _page_title(page_key: str, lang: str) -> str:
    if page_key in ENTITY_PAGES:
        return get_text(f"entity_tabs.{page_key}", lang)
    if page_key in TREE_PAGES:
        return get_text(f"tree_tabs.{page_key}", lang)
    return get_text(f"nav.{page_key}", lang)


def _make_page(page_key: str, lang: str) -> st.Page:
    render = _renderer(page_key)

    def _run() -> None:
        render(st.session_state["lang"])

    _run.__name__ = f"page_{page_key}"
    return st.Page(
        _run,
        title=_page_title(page_key, lang),
        url_path=URL_PATHS[page_key],
        default=page_key == PAGE_HOME,
    )


def _build_navigation(lang: str):
    """Every page has its own URL (see system_common/UrlPaths.py)."""
    pages = {key: _make_page(key, lang) for key in URL_PATHS}
    navigation.register_pages(pages)
    groups = {
        "": [pages[k] for k in (PAGE_HOME, PAGE_ABOUT, PAGE_NUMBER_SEARCH, PAGE_SOURCE_SEARCH)],
        get_text("nav.entity_search", lang): [pages[PAGE_ENTITY_SEARCH]] + [pages[k] for k in ENTITY_PAGES],
        get_text("nav.trees", lang): [pages[PAGE_TREES]] + [pages[k] for k in TREE_PAGES],
    }
    page = st.navigation(groups, position="top")
    _render_mobile_menu(groups, lang)
    return page


def _render_mobile_menu(groups: dict, lang: str) -> None:
    """Streamlit drops the top nav on narrow screens; this menu is shown only there (see styles.css)."""
    with st.container(key="mobile_nav"):
        with st.popover("\u2630 " + get_text("ui.menu", lang), use_container_width=True):
            for title, group_pages in groups.items():
                if title:
                    st.caption(title)
                for p in group_pages:
                    st.page_link(p)


MAIN_IMAGE = FRONTEND_DIR / "icons" / "optimized" / "eitz_habina_main_image.jpg"


def main() -> None:
    st.set_page_config(page_title="Eitz Habinah | \u05e2\u05e5 \u05d4\u05d1\u05d9\u05e0\u05d4", layout="wide")

    _init_state()
    apply_layout(st.session_state["lang"])

    # Header row: language selector on far side
    header_cols = st.columns([4, 1])
    with header_cols[1]:
        selected_lang = language_selector(st.session_state["lang"])
        if selected_lang != st.session_state["lang"]:
            st.session_state["lang"] = selected_lang
            st.rerun()
    lang = st.session_state["lang"]

    with header_cols[0]:
        render_header(lang, MAIN_IMAGE)

    page = _build_navigation(lang)
    if page.url_path != URL_PATHS[PAGE_STUDIED_FROM]:
        st.session_state.pop("studied_from_warning_shown", None)
    if page.url_path != URL_PATHS[PAGE_SYMBOLS]:
        st.session_state.pop(entity_search.SYMBOLS_WARNING_SHOWN_KEY, None)
    page.run()


if __name__ == "__main__":
    main()