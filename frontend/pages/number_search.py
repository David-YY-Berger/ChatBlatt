# bs"d - lehagdil torah velahadir
"""
Number-search page.

UI responsibilities only:
  - search bar (single free-form input box + search button) laid out in one row
  - number type (whole vs. fraction) is auto-detected from the input, not user-selected
  - live input validation with specific, descriptive error messages
  - result display: big number header → coloured category tabs → sorted table

All search logic lives in number_search_logic.py via NumberSearchController.
"""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as st_components

from translations1 import get_text, is_rtl
from system_common.SystemFunctions import get_secret

_DEBUG_FE = get_secret("PRINT_DEBUG_LOGS_FE").strip().lower() == "true"

from backend.app.controllers.number_search_controller import (
    NumberSearchController,
    NumberSearchRequest,
    NumberSearchResponse,
    UnitSearchRequest,
)
from backend.app.logic.number_search_logic import NumberSearchResult, NumberOccurrenceDTO
from backend.models_db.Enums import NumberCategory
from system_common.Constants import NUMBER_TYPE_WHOLE, NUMBER_TYPE_FRACTION
from frontend.components.source_popup import (
    source_popup_css_js,
    source_popup_html,
    source_link_html,
)


# ---------------------------------------------------------------------------
# Category display configuration
# ---------------------------------------------------------------------------

_CATEGORY_CONFIG: dict = {
    NumberCategory.Sacrifice:    {"emoji": "🔥", "color": "#e85d04"},
    NumberCategory.Time:         {"emoji": "⏳", "color": "#1d6fa4"},
    NumberCategory.Money:        {"emoji": "💰", "color": "#b8860b"},
    NumberCategory.People:       {"emoji": "👥", "color": "#2d6a4f"},
    NumberCategory.Measurement:  {"emoji": "📏", "color": "#6d28d9"},
    NumberCategory.Obligation:   {"emoji": "📜", "color": "#0f766e"},
    NumberCategory.Gematria:     {"emoji": "🔢", "color": "#7c2d12"},
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


_CHEVRON_SVG = (
    "<svg class='chev' viewBox='0 0 20 20' width='16' height='16' fill='none' "
    "stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'>"
    "<polyline points='6,8 10,12 14,8'/></svg>"
)


def _group_by_unit(occurrences: list[NumberOccurrenceDTO]) -> list[tuple[str | None, list[dict]]]:
    """Group occurrences by unit, then by source.

    Returns ``[(unit, [{"occ": first_occ, "contexts": [...]}, ...]), ...]`` with
    units sorted alphabetically (no-unit last) and sources in their incoming
    (canonical) order. Contexts of the same source are merged and de-duplicated.
    """
    by_unit: dict[str | None, dict[str, dict]] = {}
    for occ in occurrences:
        sources = by_unit.setdefault(occ.en_unit or None, {})
        g = sources.setdefault(occ.source_key, {"occ": occ, "contexts": []})
        if occ.en_context and occ.en_context not in g["contexts"]:
            g["contexts"].append(occ.en_context)
    ordered = sorted(by_unit, key=lambda u: (u is None, (u or "").lower()))
    return [(u, list(by_unit[u].values())) for u in ordered]


def _occurrences_table(
    occurrences: list[NumberOccurrenceDTO],
    accent: str,
    source_contents: dict,
) -> tuple[str, int]:
    """
    Return ``(full_html, iframe_height)`` for the given occurrences.

    Organised by unit: every unit is a collapsed card (chevron + name + source
    count). Opening it reveals one row per source with its contexts and summary.
    ``source_contents`` maps source_key → SourceContent (or None).
    """
    units = _group_by_unit(occurrences)
    border_col = _hex_rgba(accent, 0.25)

    cards_html = []
    popup_html_parts = []
    seen_popup_keys: set[str] = set()

    for unit, sources in units:
        rows = []
        for g in sources:
            occ = g["occ"]
            src_content = source_contents.get(occ.source_key)
            if src_content is not None:
                source_cell = source_link_html(occ.source_key, occ.source_str, color=accent)
            else:
                source_cell = html.escape(occ.source_str or "—")

            if g["contexts"]:
                ctx_cell = "<ul>" + "".join(f"<li>{html.escape(c.lstrip('* ').strip())}</li>" for c in g["contexts"]) + "</ul>"
            else:
                ctx_cell = "—"

            rows.append(
                f"<tr><td>{ctx_cell}</td>"
                f"<td class='summary-cell'>{html.escape(occ.summary or '—')}</td>"
                f"<td class='src'>{source_cell}</td></tr>"
            )

            if src_content is not None and occ.source_key not in seen_popup_keys:
                seen_popup_keys.add(occ.source_key)
                content_list = src_content._get_content() if hasattr(src_content, "_get_content") else getattr(src_content, "content", [])
                popup_html_parts.append(
                    source_popup_html(
                        source_key=occ.source_key,
                        title_en=occ.source_str_en,
                        title_heb=occ.source_str_heb,
                        en_content=content_list[0] if len(content_list) > 0 else "",
                        heb_content=content_list[1] if len(content_list) > 1 else "",
                    )
                )

        n = len(sources)
        name = html.escape(unit) if unit else "<i>no unit</i>"
        cards_html.append(
            "<div class='unit-card'>"
            "<button class='unit-head' type='button' onclick='toggleUnit(this)' aria-expanded='false'>"
            f"{_CHEVRON_SVG}<span class='unit-name'>{name}</span>"
            f"<span class='cnt'>{n} source{'s' if n != 1 else ''}</span></button>"
            "<div class='unit-body' hidden><table><thead><tr>"
            "<th>Context</th><th>Source Summary</th><th>Source</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div></div>"
        )

    style = f"""<style>
  :root {{ color-scheme: dark; --accent:{accent}; --accent-border:{border_col};
          --accent-bg:{_hex_rgba(accent, 0.10)}; --accent-soft:{_hex_rgba(accent, 0.06)};
          --accent-hover:{_hex_rgba(accent, 0.13)}; }}
  body {{ background:#0e1117; color:#e2e8f0; margin:0; padding:0.5rem 0 0 0;
         font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  .unit-card {{ border:1px solid var(--accent-border); border-radius:10px; margin-bottom:0.55rem;
               overflow:hidden; background:var(--accent-soft); transition:box-shadow .2s; }}
  .unit-card.open {{ box-shadow:0 0 0 1px var(--accent-border), 0 4px 14px rgba(0,0,0,.35); }}
  .unit-head {{ all:unset; box-sizing:border-box; width:100%; display:flex; align-items:center;
               gap:0.7rem; padding:0.65rem 0.9rem; cursor:pointer; color:inherit; }}
  .unit-head:hover {{ background:var(--accent-hover); }}
  .unit-head:focus-visible {{ outline:2px solid var(--accent); outline-offset:-2px; }}
  .chev {{ flex:none; color:var(--accent); transition:transform .2s ease; transform:rotate(-90deg); }}
  .unit-head[aria-expanded='true'] .chev {{ transform:rotate(0deg); }}
  .unit-name {{ font-weight:700; font-size:1rem; flex:1; }}
  .cnt {{ font-size:0.72rem; font-weight:700; color:var(--accent); background:var(--accent-bg);
         border:1px solid var(--accent-border); border-radius:999px; padding:2px 10px; }}
  .unit-body {{ border-top:1px solid var(--accent-border); background:#0e1117;
               animation:fadeIn .2s ease; overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ padding:0.45rem 0.9rem; text-align:left; font-size:0.72rem; text-transform:uppercase;
       letter-spacing:.07em; color:var(--accent); background:var(--accent-bg); white-space:nowrap; }}
  td {{ padding:0.5rem 0.9rem; vertical-align:top; font-size:0.875rem; line-height:1.45;
       border-top:1px solid {_hex_rgba(accent, 0.12)}; }}
  td.src {{ white-space:nowrap; }}
  td ul {{ margin:0; padding-left:1.1rem; }}
  td li {{ margin:0.15rem 0; }}
  .summary-cell {{ color:#94a3b8; }}
  @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(-3px); }} to {{ opacity:1; transform:none; }} }}
</style>"""

    script = """<script>
function toggleUnit(btn) {
  var body = btn.nextElementSibling;
  var open = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', open ? 'false' : 'true');
  btn.parentElement.classList.toggle('open', !open);
  body.hidden = open;
  resizeFrame();
}
function resizeFrame() {
  try {
    var h = Math.max(document.body.scrollHeight + 24, 520);
    window.frameElement.style.height = h + 'px';
  } catch (e) {}
}
</script>"""

    full_html = (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        + style
        + source_popup_css_js()
        + "</head><body>"
        + "".join(cards_html)
        + "".join(popup_html_parts)
        + script
        + "</body></html>"
    )

    return full_html, 520

# ---------------------------------------------------------------------------
# Source content fetching
# ---------------------------------------------------------------------------

def _fetch_source_contents(result: NumberSearchResult) -> dict:
    """
    Fetch SourceContent objects for all unique source keys in *result*.
    Results are cached in session_state to avoid repeated DB calls on re-renders.
    Returns a dict mapping source_key → SourceContent (or None on error).
    """
    cache_key = "number_search_source_contents"
    cached: dict | None = st.session_state.get(cache_key)
    if cached is not None:
        return cached

    unique_keys: set[str] = set()
    for occurrences in result.by_category.values():
        for occ in occurrences:
            unique_keys.add(occ.source_key)

    from backend.db.DBFactory import DBFactory
    db = DBFactory.get_prod_db_mongo()

    contents: dict = {}
    for key in unique_keys:
        try:
            contents[key] = db.find_one_source_content(key)
        except Exception:
            contents[key] = None

    st.session_state[cache_key] = contents
    return contents




def _detect_number_type(value: str) -> str:
    """Auto-detect whether *value* is meant to be a whole number or a fraction.

    A single '/' indicates a fraction (e.g. "1/3"); anything else is treated
    as a whole number. This keeps the UI to a single free-form input while
    still allowing type-specific validation messages.
    """
    return NUMBER_TYPE_FRACTION if "/" in value else NUMBER_TYPE_WHOLE


def _validate_number(value: str) -> str | None:
    """Return a descriptive error message, or None when the input is valid.

    The number type (whole vs. fraction) is auto-detected from *value* —
    there is no separate type selector in the UI.
    """
    s = value.strip()
    if not s:
        return None  # Empty — silently ignored until Search is clicked

    number_type = _detect_number_type(s)

    if number_type == NUMBER_TYPE_WHOLE:
        if "." in s:
            return "❌ Decimal points aren't supported — enter a whole number (e.g. 7) or a fraction (e.g. 1/3)"
        if "-" in s:
            return "❌ Negative numbers are not allowed"
        if not s.isdigit():
            return "❌ Only digits (0–9) are allowed, or a fraction like 1/3"
        if int(s) in (0, 1):
            return "❌ Number must be greater than 1 (0 and 1 are not allowed)"

    else:  # fraction
        if "-" in s:
            return "❌ Negative numbers are not allowed"
        if "." in s:
            return "❌ Fractions cannot contain decimal points"
        slash_count = s.count("/")
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
        if int(num_s) == int(den_s):
            return "❌ A fraction equal to 1 is not allowed (0 and 1 are not allowed)"

    return None  # Input is valid


# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------

def _on_search_submit(lang: str) -> None:
    """Callback for the search input's on_change — runs the search when the
    user presses Enter (text_input fires on_change on Enter or blur)."""
    value = st.session_state.get("number_input", "")
    if not value.strip():
        return
    if _validate_number(value) is None:
        _run_search(value.strip(), lang)


def _render_search_bar(lang: str) -> None:
    """Render the inline search bar: input | search button.

    A single free-form input accepts either a whole number (e.g. "7") or a
    fraction (e.g. "1/3"); the placeholder and helper caption make both
    supported formats clear since there's no separate type selector.
    """
    input_col, btn_col = st.columns([8, 1], vertical_alignment="bottom")

    with input_col:
        value = st.text_input(
            get_text("number_search_ui.input_label", lang),
            placeholder=get_text("number_search_ui.placeholder", lang),
            help=get_text("number_search_ui.format_hint", lang),
            key="number_input",
            # on_change fires when the user presses Enter (or the field loses
            # focus after an edit), so Enter triggers a search just like the button.
            on_change=_on_search_submit,
            args=(lang,),
        )

    with btn_col:
        search_clicked = st.button(
            get_text("number_search_ui.search_button", lang),
            use_container_width=True,
            type="primary",
            key="number_search_btn",
            # Run the search in a callback (before the script rerun) so no
            # stale duplicate of the bar is drawn while the search executes.
            on_click=_on_search_submit,
            args=(lang,),
        )

    # Live validation — runs on every rerender (i.e. every keystroke / widget change)
    error = _validate_number(value)

    if search_clicked and not value.strip():
        error = get_text("number_search_ui.error_empty", lang)

    if error:
        st.markdown(
            f'<p style="color:#ef4444; font-size:0.875rem; margin:0.3rem 0 0 0;">{error}</p>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Search execution
# ---------------------------------------------------------------------------

def _run_search(value: str, lang: str) -> None:
    """Pass the validated input to the controller and store the response in session state."""
    controller = NumberSearchController()
    request = NumberSearchRequest(value=value, lang=lang)
    response = controller.handle(request)
    if _DEBUG_FE:
        _debug_log_result(request, response)
    st.session_state["number_search_response"] = response
    st.session_state["number_search_value"] = value
    # Clear cached source contents so they're re-fetched for the new result
    st.session_state.pop("number_search_source_contents", None)


def _run_unit_search(unit: str, lang: str) -> None:
    response = NumberSearchController().handle_unit(UnitSearchRequest(unit=unit, lang=lang))
    st.session_state["unit_search_response"] = response
    st.session_state["unit_search_value"] = unit


# ---------------------------------------------------------------------------
# Debug logging
# ---------------------------------------------------------------------------

def _debug_log_result(request: "NumberSearchRequest", response: "NumberSearchResponse") -> None:
    """When PRINT_DEBUG_LOGS_FE=true, prints the search request and full result to the console."""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"[DEBUG FE] Number search: value={request.value}  lang={request.lang}")
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
            unit_label = occ.en_unit or "(no unit)"
            print(f"    [{unit_label}]  sources: {occ.source_str}")
            if occ.en_context:
                print(f"      context : {occ.en_context}")
            if occ.summary:
                print(f"      summary : {occ.summary}")
    print(sep + "\n")


# ---------------------------------------------------------------------------
# Unit search (alternative to number search)
# ---------------------------------------------------------------------------

_MODE_NUMBER = "number"
_MODE_UNIT = "unit"


def _on_unit_submit(lang: str) -> None:
    unit = st.session_state.get("unit_input")
    if unit:
        _run_unit_search(unit, lang)


def _render_unit_search_bar(lang: str) -> None:
    """Searchable combobox: a selectbox is a dropdown whose options filter as the user types."""
    units = NumberSearchController().list_units()
    heb_by_en = dict(units)

    def _label(en: str) -> str:
        heb = heb_by_en.get(en)
        return f"{en} ({heb})" if heb else en

    input_col, btn_col = st.columns([8, 1], vertical_alignment="bottom")
    with input_col:
        value = st.selectbox(
            get_text("number_search_ui.unit_input_label", lang),
            options=[en for en, _ in units],
            index=None,
            format_func=_label,
            placeholder=get_text("number_search_ui.unit_placeholder", lang),
            help=get_text("number_search_ui.unit_format_hint", lang),
            key="unit_input",
            on_change=_on_unit_submit,
            args=(lang,),
        )
    with btn_col:
        clicked = st.button(
            get_text("number_search_ui.search_button", lang),
            use_container_width=True,
            type="primary",
            key="unit_search_btn",
            on_click=_on_unit_submit,
            args=(lang,),
        )
    if clicked and not value:
        st.markdown(
            f'<p style="color:#ef4444; font-size:0.875rem; margin:0.3rem 0 0 0;">'
            f'{get_text("number_search_ui.error_empty_unit", lang)}</p>',
            unsafe_allow_html=True,
        )

def _render_unit_results(lang: str) -> None:
    response = st.session_state.get("unit_search_response")
    if response is None:
        return
    unit: str = st.session_state.get("unit_search_value", "")

    if not response.success or response.error:
        st.error(response.error or get_text("number_search_ui.error_generic", lang))
        return
    result = response.result
    if result is None or not result.rows:
        st.warning(get_text("number_search_ui.no_unit_results", lang).format(value=unit))
        return

    st.markdown(
        f"""
        <div style="text-align:center; padding:1.25rem 0 1rem 0;">
            <div style="font-size:2.5rem; font-weight:900; line-height:1;">{html.escape(result.unit)}</div>
            <div style="font-size:0.875rem; color:#94a3b8; margin-top:0.35rem;">
                {len(result.rows)} {get_text("number_search_ui.unit_results_count", lang)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Plain HTML table: st.dataframe lazy-loads a JS chunk that fails on some deployments.
    headers = [
        get_text("number_search_ui.col_number", lang),
        get_text("number_search_ui.col_categories", lang),
        get_text("number_search_ui.col_mentions", lang),
    ]
    body = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(row.value),
            html.escape(", ".join(f"{_CATEGORY_CONFIG[c]['emoji']} {c.value}" for c in row.categories) or "—"),
            row.mentions,
        )
        for row in result.rows
    )
    st.markdown(
        "<table style='width:100%; border-collapse:collapse;'>"
        "<thead><tr>" + "".join(f"<th style='text-align:start; padding:0.4rem 0.6rem;'>{html.escape(h)}</th>" for h in headers)
        + "</tr></thead><tbody>" + body + "</tbody></table>",
        unsafe_allow_html=True,
    )

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

    # Fetch source content for popup support (cached in session_state)
    source_contents = _fetch_source_contents(result)

    by_cat = result.by_category

    # ── Big number header ──────────────────────────────────────────────────
    plural = "s" if result.total_count != 1 else ""
    st.markdown(
        f"""
        <div style="text-align:center; padding:1.25rem 0 1rem 0;">
            <div style="font-size:3.5rem; font-weight:900; letter-spacing:-0.02em;
                        color: inherit; line-height:1;">{html.escape(value)}</div>
            <div style="font-size:0.875rem; color:#94a3b8; margin-top:0.35rem;">
                {result.total_count} occurrence{plural} found
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Build ordered tab entries (all NumberCategory values + None if present) ──
    tab_entries: list[tuple] = []  # (cat, color, label)
    for cat in sorted(NumberCategory, key=lambda c: c.ordinal):
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
                f"{count} occurrence{plural} · click a unit to see its sources</p>",
                unsafe_allow_html=True,
            )

            table_html, iframe_height = _occurrences_table(occurrences, color, source_contents)
            st_components.html(table_html, height=iframe_height, scrolling=False)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render(lang: str) -> None:
    title = get_text("page_titles.number_search", lang)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

    mode = st.radio(
        "search mode",
        options=[_MODE_NUMBER, _MODE_UNIT],
        format_func=lambda m: get_text(
            "number_search_ui.mode_number" if m == _MODE_NUMBER else "number_search_ui.mode_unit", lang
        ),
        horizontal=True,
        label_visibility="collapsed",
        key="number_search_mode",
    )

    if mode == _MODE_UNIT:
        _render_unit_search_bar(lang)
        _render_unit_results(lang)
    else:
        _render_search_bar(lang)
        _render_results(lang)
