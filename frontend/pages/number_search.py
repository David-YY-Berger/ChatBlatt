# bs"d - lehagdil torah velahadir
"""
Number-search page.

UI responsibilities only:
  - search bar (type selector, input box, search button) laid out in one row
  - live input validation with specific, descriptive error messages
  - result display: big number header → coloured category tabs → sorted table

All search logic lives in number_search_logic.py via NumberSearchController.
"""

from __future__ import annotations

import html

import streamlit as st

from translations1 import get_text, is_rtl
from system_common.SystemFunctions import get_secret

_DEBUG_FE = get_secret("PRINT_DEBUG_LOGS_FE").strip().lower() == "true"

from backend.app.controllers.number_search_controller import (
    NumberSearchController,
    NumberSearchRequest,
    NumberSearchResponse,
)
from backend.app.logic.number_search_logic import NumberSearchResult, NumberOccurrenceDTO
from backend.models_db.Enums import NumberCategory
from system_common.Constants import NUMBER_TYPE_WHOLE, NUMBER_TYPE_FRACTION


# ---------------------------------------------------------------------------
# Category display configuration
# ---------------------------------------------------------------------------

_CATEGORY_CONFIG: dict = {
    NumberCategory.Sacrifice:    {"emoji": "🔥", "color": "#e85d04"},
    NumberCategory.Time:         {"emoji": "⏳", "color": "#1d6fa4"},
    NumberCategory.Money:        {"emoji": "💰", "color": "#b8860b"},
    NumberCategory.People:       {"emoji": "👥", "color": "#2d6a4f"},
    NumberCategory.Measurement:  {"emoji": "📏", "color": "#6d28d9"},
    NumberCategory.Misc:         {"emoji": "📦", "color": "#475569"},
}
_NONE_CAT_CONFIG = {"emoji": "❓", "color": "#94a3b8"}


def _hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _tab_css(colors: list[str]) -> str:
    parts: list[str] = []
    for i, col in enumerate(colors, 1):
        bg_sel = _hex_rgba(col, 0.09)
        bg_hov = _hex_rgba(col, 0.05)
        parts.append(f"""
div[data-testid="stTabs"] button[role="tab"]:nth-child({i}) {{
    color: {col};
    transition: background 0.15s, border-bottom 0.15s;
}}
div[data-testid="stTabs"] button[role="tab"]:nth-child({i})[aria-selected="true"] {{
    color: {col} !important;
    border-bottom: 3px solid {col} !important;
    background: {bg_sel};
    font-weight: 700;
}}
div[data-testid="stTabs"] button[role="tab"]:nth-child({i}):hover {{
    background: {bg_hov};
}}
""")
    return "\n".join(parts)


def _occurrences_table(occurrences: list[NumberOccurrenceDTO], accent: str) -> str:
    """Return an HTML table string for the given occurrences, sorted by Unit."""
    sorted_occs = sorted(occurrences, key=lambda o: (o.unit is None, (o.unit or "").lower()))

    header_bg = _hex_rgba(accent, 0.10)
    border_col = _hex_rgba(accent, 0.25)
    stripe_bg = _hex_rgba(accent, 0.04)

    th_style = (
        f"padding:0.55rem 0.8rem; text-align:left; font-weight:600;"
        f" color:{accent}; background:{header_bg};"
        f" border-bottom:2px solid {border_col}; white-space:nowrap;"
    )
    td_base = "padding:0.5rem 0.8rem; vertical-align:top; font-size:0.875rem; line-height:1.45;"
    border_style = f"border-bottom:1px solid {_hex_rgba(accent, 0.12)};"

    rows_html = []
    for idx, occ in enumerate(sorted_occs):
        row_bg = f"background:{stripe_bg};" if idx % 2 == 1 else ""
        unit    = html.escape(occ.unit or "—")
        context = html.escape(occ.context or "—")
        source  = html.escape(occ.source_str or "—")
        summary = html.escape(occ.summary or "—")
        rows_html.append(
            f"<tr style='{row_bg}'>"
            f"<td style='{td_base}{border_style} font-weight:500;'>{unit}</td>"
            f"<td style='{td_base}{border_style}'>{context}</td>"
            f"<td style='{td_base}{border_style} color:{accent}; font-weight:500;'>{source}</td>"
            f"<td style='{td_base}{border_style} color:#475569;'>{summary}</td>"
            f"</tr>"
        )

    table = (
        "<div style='overflow-x:auto; border-radius:8px; border:1px solid "
        + border_col + "; margin-top:0.5rem;'>"
        "<table style='width:100%; border-collapse:collapse;'>"
        "<thead><tr>"
        f"<th style='{th_style}'>Unit</th>"
        f"<th style='{th_style}'>Context</th>"
        f"<th style='{th_style}'>Source</th>"
        f"<th style='{th_style}'>Source Summary</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows_html) + "</tbody>"
        "</table></div>"
    )
    return table


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_number(value: str, number_type: str) -> str | None:
    """Return a descriptive error message, or None when the input is valid."""
    s = value.strip()
    if not s:
        return None  # Empty — silently ignored until Search is clicked

    if number_type == NUMBER_TYPE_WHOLE:
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
            options=[NUMBER_TYPE_WHOLE, NUMBER_TYPE_FRACTION],
            format_func=lambda x: (
                get_text("number_search_ui.type_whole", lang)
                if x == NUMBER_TYPE_WHOLE
                else get_text("number_search_ui.type_fraction", lang)
            ),
            key="number_type",
            horizontal=True,
        )

    with input_col:
        placeholder = (
            get_text("number_search_ui.placeholder_whole", lang)
            if number_type == NUMBER_TYPE_WHOLE
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
    """Pass the validated input to the controller and store the response in session state."""
    controller = NumberSearchController()
    request = NumberSearchRequest(number_type=number_type, value=value, lang=lang)
    response = controller.handle(request)
    if _DEBUG_FE:
        _debug_log_result(request, response)
    st.session_state["number_search_response"] = response
    st.session_state["number_search_value"] = value


# ---------------------------------------------------------------------------
# Debug logging
# ---------------------------------------------------------------------------

def _debug_log_result(request: "NumberSearchRequest", response: "NumberSearchResponse") -> None:
    """When PRINT_DEBUG_LOGS_FE=true, prints the search request and full result to the console."""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"[DEBUG FE] Number search: type={request.number_type}  value={request.value}  lang={request.lang}")
    print(sep)

    if not response.success or response.error:
        print(f"  ERROR: {response.error}")
        print(sep + "\n")
        return

    result = response.result
    if result is None:
        print("  No results found.")
        print(sep + "\n")
        return

    print(f"  Total occurrences: {result.total_count}")
    for category, occurrences in result.by_category.items():
        cat_label = category.value if category else "(no category)"
        print(f"\n  📂 {cat_label} ({len(occurrences)} occurrence(s))")
        for occ in occurrences:
            unit_label = occ.unit or "(no unit)"
            print(f"    [{unit_label}]  sources: {occ.source_str}")
            if occ.context:
                print(f"      context : {occ.context}")
            if occ.summary:
                print(f"      summary : {occ.summary}")
    print(sep + "\n")


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _render_results(lang: str) -> None:
    """Render the number header, category tabs, and occurrence table."""
    response: NumberSearchResponse | None = st.session_state.get("number_search_response")
    if response is None:
        return

    value: str = st.session_state.get("number_search_value", "")

    if not response.success or response.error:
        st.error(response.error or get_text("number_search_ui.error_generic", lang))
        return

    result: NumberSearchResult | None = response.result
    if result is None:
        st.warning(get_text("number_search_ui.no_results", lang).format(value=value))
        return

    # ── Big number header ──────────────────────────────────────────────────
    plural = "s" if result.total_count != 1 else ""
    st.markdown(
        f"""
        <div style="text-align:center; padding:1.25rem 0 1rem 0;">
            <div style="font-size:3.5rem; font-weight:900; letter-spacing:-0.02em;
                        color:#1e293b; line-height:1;">{html.escape(value)}</div>
            <div style="font-size:0.875rem; color:#64748b; margin-top:0.35rem;">
                {result.total_count} occurrence{plural} found
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Build ordered tab entries (all NumberCategory values + None if present) ──
    by_cat = result.by_category
    tab_entries: list[tuple] = []  # (cat, color, label)
    for cat in NumberCategory:
        cfg = _CATEGORY_CONFIG[cat]
        count = len(by_cat.get(cat, []))
        label = f"{cfg['emoji']} {cat.value}  ({count})"
        tab_entries.append((cat, cfg["color"], label))

    if None in by_cat:
        cfg = _NONE_CAT_CONFIG
        count = len(by_cat[None])
        tab_entries.append((None, cfg["color"], f"{cfg['emoji']} Other  ({count})"))

    # ── Inject per-tab colour CSS ──────────────────────────────────────────
    colors = [e[1] for e in tab_entries]
    st.markdown(f"<style>{_tab_css(colors)}</style>", unsafe_allow_html=True)

    # ── Render tabs ────────────────────────────────────────────────────────
    tabs = st.tabs([e[2] for e in tab_entries])

    for tab_widget, (cat, color, _) in zip(tabs, tab_entries):
        with tab_widget:
            occurrences = by_cat.get(cat, [])
            if not occurrences:
                cat_name = cat.value if cat else "other"
                st.markdown(
                    f'<p style="color:#94a3b8; padding:0.75rem 0; font-style:italic;">'
                    f"No {cat_name} occurrences for this number.</p>",
                    unsafe_allow_html=True,
                )
                continue

            count = len(occurrences)
            plural = "s" if count != 1 else ""
            st.markdown(
                f'<p style="font-size:0.8rem; color:#94a3b8; margin:0.25rem 0 0 0;">'
                f"{count} occurrence{plural}</p>",
                unsafe_allow_html=True,
            )
            st.markdown(_occurrences_table(occurrences, color), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render(lang: str) -> None:
    title = get_text("page_titles.number_search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    _render_search_bar(lang)
    _render_results(lang)
