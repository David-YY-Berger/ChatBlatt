# bs"d - lehagdil torah velahadir
"""
Standalone source popup component.

Provides CSS, JS, and HTML generation for displaying source content
(English + Hebrew) in a modal popup overlay.

All source-section styling and HTML structure is sourced from
``HtmlWriter`` — there is no duplication.

Public API
----------
source_popup_css_js()       → str   CSS + JS to inject once per HTML context
source_popup_html(...)      → str   Full overlay <div> for one source popup
source_link_html(...)       → str   <a> tag that opens a popup on click
"""

from __future__ import annotations

import html as _html
import re

from backend.file_utils.HtmlWriter import HtmlWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_id(key: str) -> str:
    """Convert an arbitrary source key to a safe HTML/JS identifier."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", key)


# ---------------------------------------------------------------------------
# CSS + JS  (include once per HTML context / iframe)
# ---------------------------------------------------------------------------

def source_popup_css_js() -> str:
    """
    Returns a <style> + <script> block needed by source popups.
    Source-section styles and toggle functions come from HtmlWriter.
    Must be included once in the HTML that hosts the popup and link elements.
    """
    popup_css = """\
/* ── Popup overlay ── */
.sp-overlay {
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,0.55);
    z-index:9999; align-items:center; justify-content:center;
}
.sp-overlay.sp-open { display:flex; }
.sp-box {
    background:white; border-radius:8px;
    width:min(820px,92vw); max-height:88vh;
    overflow-y:auto;
    box-shadow:0 8px 32px rgba(0,0,0,0.3);
    font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;
}
.sp-close-bar {
    display:flex; justify-content:flex-end; padding:8px 12px 0;
    position:sticky; top:0; background:white; z-index:1;
}
.sp-close-btn {
    border:none; background:none; font-size:1.4rem; cursor:pointer;
    color:#64748b; line-height:1; padding:0 4px;
}
.sp-close-btn:hover { color:#1e293b; }
.sp-content { padding:0 12px 12px; }"""

    popup_js = """\
function spOpen(id) {
    document.getElementById('sp-' + id).classList.add('sp-open');
}
function spClose(id) {
    document.getElementById('sp-' + id).classList.remove('sp-open');
}"""

    return (
        "<style>\n"
        + popup_css + "\n"
        + HtmlWriter.get_source_section_css()
        + "\n</style>\n"
        "<script>\n"
        + popup_js + "\n"
        + HtmlWriter.get_source_section_js()
        + "\n</script>"
    )


# ---------------------------------------------------------------------------
# Public: popup overlay HTML
# ---------------------------------------------------------------------------

def source_popup_html(
    source_key: str,
    title_en: str,
    title_heb: str,
    en_content: str,
    heb_content: str,
    summary_en: str = "",
    summary_heb: str = "",
) -> str:
    """
    Returns the full overlay <div> for one source popup.

    Place this element anywhere in the DOM (e.g. after the table).
    ``source_popup_css_js()`` must also be present in the same HTML context.

    Parameters
    ----------
    source_key  Unique key that identifies this source (used as HTML ID).
    title_en    English display title (plain text — will be escaped).
    title_heb   Hebrew display title  (plain text — will be escaped).
    en_content  English body HTML (already HTML — NOT escaped).
    heb_content Hebrew body HTML  (already HTML — NOT escaped).
    summary_en  Optional English summary line (plain text).
    summary_heb Optional Hebrew summary line  (plain text).
    """
    pid = _safe_id(source_key)
    body_id   = f"src-body-{pid}"
    header_id = f"src-hdr-{pid}"

    inner_html = HtmlWriter.build_source_content(en_content, heb_content, pid)

    source_section = HtmlWriter.build_source_section(
        body_id=body_id,
        header_id=header_id,
        title_en=title_en,
        title_heb=title_heb,
        inner_content_html=inner_html,
        summary_en=summary_en,
        summary_heb=summary_heb,
        start_open=True,
    )

    return (
        f'<div class="sp-overlay" id="sp-{pid}"'
        f' onclick="if(event.target===this)spClose(\'{pid}\')">'
        f'<div class="sp-box">'
        f'<div class="sp-close-bar">'
        f'<button class="sp-close-btn" onclick="spClose(\'{pid}\')">&#x2715;</button>'
        f'</div>'
        f'<div class="sp-content">{source_section}</div>'
        f'</div></div>'
    )


# ---------------------------------------------------------------------------
# Public: clickable link
# ---------------------------------------------------------------------------

def source_link_html(
    source_key: str,
    link_text: str,
    color: str = "#1d6fa4",
) -> str:
    """
    Returns an <a> element that opens the popup for ``source_key`` when clicked.

    ``source_popup_html(source_key, ...)`` must be present somewhere in the
    same HTML context, and ``source_popup_css_js()`` must also be included.
    """
    pid = _safe_id(source_key)
    escaped_text = _html.escape(link_text or "")
    return (
        f'<a href="javascript:void(0)" onclick="spOpen(\'{pid}\')"'
        f' style="color:{color};font-weight:500;text-decoration:underline;cursor:pointer;">'
        f'{escaped_text}</a>'
    )

