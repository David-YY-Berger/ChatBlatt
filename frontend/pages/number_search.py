# bs"d - lehagdil torah velahadir
"""
Number-search page.

UI responsibilities only:
  - search bar (type selector, input box, search button) laid out in one row
  - live input validation with specific, descriptive error messages
  - result display (coming soon)

All search logic will live in number_search_logic.py via NumberSearchController.
"""

from __future__ import annotations

import streamlit as st

from translations1 import get_text, is_rtl
from backend.app.controllers.number_search_controller import (
    NumberSearchController,
    NumberSearchRequest,
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_number(value: str, number_type: str) -> str | None:
    """Return a descriptive error message, or None when the input is valid."""
    s = value.strip()
    if not s:
        return None  # Empty — silently ignored until Search is clicked

    if number_type == "whole":
        if "/" in s:
            return "❌ Whole numbers cannot contain '/' — did you mean to select 'Fraction'?"
        if "." in s:
            return "❌ Whole numbers cannot contain decimal points"
        if "-" in s:
            return "❌ Negative numbers are not allowed"
        if not s.isdigit():
            return "❌ Only digits (0–9) are allowed for whole numbers"
        if int(s) == 0:
            return "❌ Number must be greater than 0 (0 is not allowed)"

    else:  # fraction
        if "-" in s:
            return "❌ Negative numbers are not allowed"
        if "." in s:
            return "❌ Fractions cannot contain decimal points"
        slash_count = s.count("/")
        if slash_count == 0:
            return "❌ Fractions must include '/' — e.g. 1/3"
        if slash_count > 1:
            return "❌ Too many '/' — fractions have exactly one slash (e.g. 1/4)"
        if not all(c in "0123456789/" for c in s):
            return "❌ Only digits and '/' are allowed in a fraction"
        num_s, den_s = s.split("/")
        if not num_s:
            return "❌ Numerator is missing — e.g. 1/3"
        if not den_s:
            return "❌ Denominator is missing — e.g. 1/3"
        if int(num_s) == 0:
            return "❌ Numerator must be greater than 0"
        if int(den_s) == 0:
            return "❌ Denominator cannot be zero"

    return None  # Input is valid


# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------

def _render_search_bar(lang: str) -> None:
    """Render the inline search bar: type selector | input | search button."""
    type_col, input_col, btn_col = st.columns([3, 5, 1], vertical_alignment="bottom")

    with type_col:
        number_type = st.radio(
            get_text("number_search_ui.type_label", lang),
            options=["whole", "fraction"],
            format_func=lambda x: (
                get_text("number_search_ui.type_whole", lang)
                if x == "whole"
                else get_text("number_search_ui.type_fraction", lang)
            ),
            key="number_type",
            horizontal=True,
        )

    with input_col:
        placeholder = (
            get_text("number_search_ui.placeholder_whole", lang)
            if number_type == "whole"
            else get_text("number_search_ui.placeholder_fraction", lang)
        )
        value = st.text_input(
            get_text("number_search_ui.input_label", lang),
            placeholder=placeholder,
            key="number_input",
        )

    with btn_col:
        search_clicked = st.button(
            get_text("number_search_ui.search_button", lang),
            use_container_width=True,
            type="primary",
            key="number_search_btn",
        )

    # Live validation — runs on every rerender (i.e. every keystroke / widget change)
    error = _validate_number(value, number_type)

    if search_clicked:
        if not value.strip():
            error = get_text("number_search_ui.error_empty", lang)
        if not error:
            _run_search(number_type, value.strip(), lang)

    if error:
        st.markdown(
            f'<p style="color:#ef4444; font-size:0.875rem; margin:0.3rem 0 0 0;">{error}</p>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Search execution
# ---------------------------------------------------------------------------

def _run_search(number_type: str, value: str, lang: str) -> None:
    """Pass the validated input to the controller and display the response."""
    controller = NumberSearchController()
    request = NumberSearchRequest(number_type=number_type, value=value)
    response = controller.handle(request)
    if response.error:
        st.error(response.error)
    else:
        st.info(get_text("number_search_ui.coming_soon", lang))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render(lang: str) -> None:
    title = get_text("page_titles.number_search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    _render_search_bar(lang)

    st.divider()
    # Results will be rendered here once number_search_logic is implemented
