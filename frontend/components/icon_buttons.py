# bs"d - lehagdil torah velahadir
"""Compact image buttons shared by entity pages; the same icons are used on the Descendants page."""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Callable

import streamlit as st

ICON_DIR = Path(__file__).resolve().parents[1] / "icons" / "optimized"
ICON_PERSON = "entity_search_main.jpg"
ICON_SOURCES = "source_search_main.jpg"
ICON_FAMILY_TREE = "family_tree.jpg"
ICON_PLACES_VISITED = "places_visited.jpg"


@lru_cache(maxsize=None)
def icon_data_uri(icon_name: str) -> str:
    encoded = base64.b64encode((ICON_DIR / icon_name).read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def render_icon_buttons(buttons: list[tuple[str, str, str, Callable[[], None]]]) -> None:
    """Render a tight row of clickable icons: (name, icon file, hint, on_click) per button."""
    if not buttons:
        return
    with st.container(key="icon_button_row"):
        for column, (name, icon_name, hint, on_click) in zip(st.columns(len(buttons)), buttons):
            with column:
                with st.container(key=f"icon_btn_{name}"):
                    st.image(ICON_DIR / icon_name, width=44)
                    if st.button(hint, key=f"icon_action_{name}", help=hint):
                        on_click()
