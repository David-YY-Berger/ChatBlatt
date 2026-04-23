# bs"d - lehagdil torah velahadir

from __future__ import annotations

import sys
from pathlib import Path

# Add frontend directory to path for imports
FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

import streamlit as st

from components.header import render_header
from components.layout import apply_layout, language_selector
from translations1 import get_text, is_rtl
from pages import about, entity_search, home, maps, search


def _init_state() -> None:
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "home"


def _nav_items(lang: str) -> list[dict]:
    return [
        {"key": "home", "label": get_text("nav.home", lang), "children": []},
        {"key": "about", "label": get_text("nav.about", lang), "children": []},
        {"key": "search", "label": get_text("nav.search", lang), "children": []},
        {
            "key": "entity_search",
            "label": get_text("nav.entity_search", lang),
            "children": [
                {"key": "people", "label": get_text("entity_tabs.people", lang)},
                {"key": "places", "label": get_text("entity_tabs.places", lang)},
                {"key": "nations", "label": get_text("entity_tabs.nations", lang)},
                {"key": "symbols", "label": get_text("entity_tabs.symbols", lang)},
            ],
        },
        {
            "key": "maps",
            "label": get_text("nav.maps", lang),
            "children": [
                {"key": "genology", "label": get_text("map_tabs.genology", lang)},
                {"key": "studied_from", "label": get_text("map_tabs.studied_from", lang)},
            ],
        },
    ]


def _render_nav(nav_items: list[dict], lang: str) -> str:
    rtl = is_rtl(lang)
    # Reverse order for RTL so tabs appear mirrored
    display_items = list(reversed(nav_items)) if rtl else nav_items
    active_page = st.session_state.get("active_page", "home")

    cols = st.columns(len(display_items))
    for idx, item in enumerate(display_items):
        # Check if this item or one of its children is active
        is_active = active_page == item["key"] or any(
            child["key"] == active_page for child in item.get("children", [])
        )
        label = f"• {item['label']}" if is_active else item["label"]
        btn_type = "primary" if is_active else "secondary"

        with cols[idx]:
            if item.get("children"):
                # Parent with children: use popover as the button itself
                with st.popover(label, use_container_width=True):
                    for child in item["children"]:
                        child_active = active_page == child["key"]
                        child_label = f"› {child['label']}" if child_active else child["label"]
                        child_type = "primary" if child_active else "secondary"
                        if st.button(child_label, key=f"sub_{child['key']}_{lang}", use_container_width=True, type=child_type):
                            st.session_state["active_page"] = child["key"]
                            st.rerun()
            else:
                # Simple nav item
                if st.button(label, key=f"nav_{item['key']}_{lang}", use_container_width=True, type=btn_type):
                    st.session_state["active_page"] = item["key"]
                    st.rerun()

    return st.session_state.get("active_page", "home")


def _render_page(page_key: str, lang: str) -> None:
    if page_key == "home":
        home.render(lang)
    elif page_key == "about":
        about.render(lang)
    elif page_key == "search":
        search.render(lang)
    elif page_key in ("entity_search", "people", "places", "nations", "symbols"):
        entity_search.render(lang, selected=page_key if page_key != "entity_search" else None)
    elif page_key in ("maps", "genology", "studied_from"):
        maps.render(lang, selected=page_key if page_key != "maps" else None)
    else:
        home.render(lang)


def main() -> None:
    st.set_page_config(page_title="Mapalee | מפה-לי", layout="wide")

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
        render_header(lang)

    nav_items = _nav_items(lang)
    active_page = _render_nav(nav_items, lang)
    _render_page(active_page, lang)


if __name__ == "__main__":
    main()
