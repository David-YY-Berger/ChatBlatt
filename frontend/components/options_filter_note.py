# bs"d - lehagdil torah velahadir

"""
Options-filter note (shared infra).

A subtle caption telling the user that a select list is pre-filtered by some
condition, e.g. "Only showing options with a family relationship".

To reuse for a new condition:
  1. Add a translation under `options_filter_conditions.<condition>` (en + he).
  2. Call `render_options_filter_note(lang, "<condition>")` next to the select list.
"""

from __future__ import annotations

import streamlit as st

from translations1 import get_text


def render_options_filter_note(lang: str, condition: str) -> None:
    """Render the 'only showing options with <condition>' caption."""
    st.caption(get_text("ui.options_filter_note", lang).format(
        condition=get_text(f"options_filter_conditions.{condition}", lang),
    ))
