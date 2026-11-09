from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend.models_db.Enums import PassageType
from system_common import SystemFunctions
from backend.models_db.Answer import Answer
from typing import List, Optional

class HtmlWriter:

    # ------------------------------------------------------------------
    # Shared static helpers (also used by frontend/components/source_popup.py)
    # ------------------------------------------------------------------

    @staticmethod
    def get_source_section_css() -> str:
        """CSS rules for source sections and collapsible content blocks.
        Shared with the frontend popup component — edit here to update both."""
        return """\
/* --- Source section collapsible --- */
.source-section { margin-bottom:6px; border:1px solid #ccc; border-radius:6px; overflow:hidden; }
.source-header { background:#34495e; color:white; padding:8px 12px; cursor:pointer; user-select:none; display:flex; flex-direction:column; gap:4px; position:relative; }
.source-header:hover { background:#2c3e50; }
.source-title-row { display:flex; align-items:center; justify-content:space-between; font-size:1em; font-weight:bold; gap:8px; }
.source-title-en { flex:1; text-align:left; }
.source-title-right { display:flex; align-items:center; gap:8px; }
.source-title-heb { direction:rtl; text-align:right; font-weight:bold; }
.source-arrow { font-size:12px; transition:transform 0.25s; flex-shrink:0; }
.source-header.open .source-arrow { transform:rotate(90deg); }
.source-summary-row { display:flex; justify-content:space-between; align-items:baseline; gap:12px; }
.source-summary-en { font-size:0.8em; color:#bdc3c7; font-weight:normal; font-style:italic; flex:1; text-align:left; }
.source-summary-heb { font-size:0.8em; color:#bdc3c7; font-weight:normal; font-style:italic; direction:rtl; text-align:right; flex:1; }
/* --- Passage-type badges --- */
.source-passage-badges { display:flex; flex-wrap:wrap; gap:0.35rem; }
.passage-badge { display:inline-flex; align-items:center; gap:0.3rem; padding:0.15rem 0.55rem; border-radius:999px; font-size:0.75em; font-weight:600; white-space:nowrap; }
.source-copy-btn { background:none; border:none; color:white; cursor:pointer; padding:2px 4px; line-height:0; border-radius:4px; opacity:0.85; }
.source-copy-btn:hover { background:rgba(255,255,255,0.2); opacity:1; }
.source-copy-btn.copied { color:#2ecc71; }
/* --- Source body --- */
.source-body { display:none; padding:8px 10px; background:white; }
.source-body.open { display:block; }
/* --- Inner content collapsible --- */
.collapsible { background-color:#3498db; color:white; cursor:pointer; padding:6px 12px; width:100%; border:none; text-align:left; outline:none; font-size:13px; border-radius:3px; margin:4px 0 2px 0; transition:background 0.2s; position:relative; }
.collapsible:hover { background-color:#2980b9; }
.collapsible.active { background-color:#27ae60; }
.collapsible::after { content:'▼'; position:absolute; right:12px; top:50%; transform:translateY(-50%); font-size:11px; transition:transform 0.2s; }
.collapsible:not(.active)::after { content:'▶'; }
.content { padding:0; max-height:0; overflow:hidden; transition:max-height 0.3s ease-out; background:#f8f9fa; border-radius:0 0 3px 3px; }
.content.active { max-height:3000px; padding:8px; }
.hebrew-content { direction:rtl; text-align:right; font-size:1.05em; line-height:1.7; margin-bottom:6px; padding:8px 10px; background:#fff; border-right:4px solid #e74c3c; border-radius:3px; }
.english-content { direction:ltr; text-align:left; font-size:0.95em; line-height:1.55; margin-bottom:6px; padding:8px 10px; background:#f8f9fa; border-left:4px solid #2ecc71; border-radius:3px; }
.no-content { color:#7f8c8d; font-style:italic; padding:10px; text-align:center; font-size:0.9em; }"""

    @staticmethod
    def get_container_css() -> str:
        """CSS for the white rounded content container that hosts source
        sections. Shared with the frontend popup component — edit here to
        update both. ``color`` is set explicitly so the container always
        renders readable dark text, regardless of the host page's own
        (possibly dark-themed) body color."""
        return """\
.container { max-width:1000px; margin:0 auto; background:white; color:#1a1a1a; padding:10px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.1); }"""

    @staticmethod
    def get_source_section_js() -> str:
        """JavaScript for toggling source sections and collapsible content.
        Shared with the frontend popup component — edit here to update both."""
        return r"""function _scEsc(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function _scPlain(html) {
    var d = document.createElement('div');
    d.innerHTML = (html || '').replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|li|h[1-6])>/gi, '</$1>\n');
    return d.textContent.replace(/\n{3,}/g, '\n\n').trim();
}
function copySource(ev, headerId) {
    ev.stopPropagation();
    var btn = ev.currentTarget;
    var section = document.getElementById(headerId).parentNode;
    var txt = function (sel) { var n = section.querySelector(sel); return n ? n.textContent.trim() : ''; };
    var htmlOf = function (sel) { var n = section.querySelector(sel); return n ? n.innerHTML : ''; };
    var blocks = [
        { t: txt('.source-title-heb'), s: txt('.source-summary-heb'), c: htmlOf('.hebrew-content'), dir: 'rtl' },
        { t: txt('.source-title-en'), s: txt('.source-summary-en'), c: htmlOf('.english-content'), dir: 'ltr' }
    ];
    var richParts = [], plainParts = [];
    blocks.forEach(function (b) {
        var rich = '', plain = [];
        if (b.t) { rich += '<p dir="' + b.dir + '"><b>' + _scEsc(b.t) + '</b></p>'; plain.push(b.t); }
        if (b.s) { rich += '<p dir="' + b.dir + '"><i>' + _scEsc(b.s) + '</i></p>'; plain.push(b.s); }
        if (b.c && b.c.trim()) { rich += '<div dir="' + b.dir + '">' + b.c + '</div>'; plain.push(_scPlain(b.c)); }
        if (rich) { richParts.push(rich); plainParts.push(plain.join('\n\n')); }
    });
    var richHtml = richParts.join('<br>');
    var plainText = plainParts.join('\n\n\n');
    var done = function () {
        btn.classList.add('copied');
        setTimeout(function () { btn.classList.remove('copied'); }, 1200);
    };
    var fallback = function () {
        var holder = document.createElement('div');
        holder.contentEditable = 'true';
        holder.style.cssText = 'position:fixed;left:-9999px;top:0;';
        holder.innerHTML = richHtml;
        document.body.appendChild(holder);
        var range = document.createRange();
        range.selectNodeContents(holder);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        try { document.execCommand('copy'); done(); } catch (e) {}
        sel.removeAllRanges();
        document.body.removeChild(holder);
    };
    try {
        navigator.clipboard.write([new ClipboardItem({
            'text/html': new Blob([richHtml], { type: 'text/html' }),
            'text/plain': new Blob([plainText], { type: 'text/plain' })
        })]).then(done, fallback);
    } catch (e) { fallback(); }
}
function toggleSource(bodyId, headerId) {
    var body = document.getElementById(bodyId);
    var header = document.getElementById(headerId);
    body.classList.toggle('open');
    header.classList.toggle('open');
}
function toggleCollapsible(contentId) {
    var content = document.getElementById(contentId);
    var button = content.previousElementSibling;
    content.classList.toggle('active');
    button.classList.toggle('active');
}"""

    @staticmethod
    def build_passage_badges_html(passage_types: Optional[List[PassageType]], labels=None) -> str:
        """Build the colorful row of passage-type badges (e.g. Law, Story of Tanach,
        Prophecy) shown on a source's header. Each :class:`PassageType`
        member supplies its own icon + color, so a source with multiple
        passage types simply gets one badge per type.
        Shared with the frontend popup component."""
        if not passage_types:
            return ""
        badges = "".join(
            f'<span class="passage-badge" style="background:{pt.color}1f; '
            f'border:1px solid {pt.color}; color:{pt.color};">'
            f'{pt.icon} {HtmlWriter._escape_html((labels or {}).get(pt.name, pt.value))}</span>'
            for pt in passage_types
        )
        return f'<div class="source-passage-badges">{badges}</div>'

    @staticmethod
    def build_source_section(
        body_id: str,
        header_id: str,
        title_en: str,
        title_heb: str,
        inner_content_html: str,
        summary_en: str = "",
        summary_heb: str = "",
        start_open: bool = False,
        passage_types: Optional[List[PassageType]] = None,
        labels=None,
    ) -> str:
        """Build a source section div (collapsible header + body).
        Shared with the frontend popup component."""
        t_en  = HtmlWriter._escape_html(title_en)
        t_heb = HtmlWriter._escape_html(title_heb)
        s_en  = HtmlWriter._escape_html(summary_en)
        s_heb = HtmlWriter._escape_html(summary_heb)

        summary_row = ""
        if s_en or s_heb:
            summary_row = (
                f'<div class="source-summary-row">'
                f'<span class="source-summary-en">{s_en}</span>'
                f'<span class="source-summary-heb">{s_heb}</span>'
                f'</div>'
            )

        labels = labels or {}
        badges_row = HtmlWriter.build_passage_badges_html(passage_types, labels.get("passage_types"))

        open_cls = " open" if start_open else ""
        return (
            f'<div class="source-section">'
            f'<div class="source-header{open_cls}" id="{header_id}"'
            f' onclick="toggleSource(\'{body_id}\', \'{header_id}\')">'
            f'<div class="source-title-row">'
            f'<span class="source-title-en">{t_en}</span>'
            f'<div class="source-title-right">'
            f'<span class="source-title-heb">{t_heb}</span>'
            f'<button class="source-copy-btn" title="{HtmlWriter._escape_html(labels.get("copy", "Copy"))}" onclick="copySource(event, \'{header_id}\')">'
            f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>'
            f'<span class="source-arrow">▶</span>'
            f'</div></div>'
            f'{badges_row}'
            f'{summary_row}'
            f'</div>'
            f'<div class="source-body{open_cls}" id="{body_id}">'
            f'{inner_content_html}'
            f'</div></div>'
        )

    @staticmethod
    def build_source_content(en_content: str, heb_content: str, idx: str, labels=None) -> str:
        """Build the collapsible Hebrew + English content blocks.
        Shared with the frontend popup component.
        ``idx`` is a unique string used as part of the element IDs."""
        labels = labels or {}
        result = ""
        if heb_content and heb_content.strip():
            result += (
                f'<button class="collapsible active"'
                f' onclick="toggleCollapsible(\'hebrew-{idx}\')">{HtmlWriter._escape_html(labels.get("hebrew_content", "Hebrew Content"))}</button>'
                f'<div class="content active" id="hebrew-{idx}">'
                f'<div class="hebrew-content">{heb_content}</div></div>'
            )
        if en_content and en_content.strip():
            result += (
                f'<button class="collapsible active"'
                f' onclick="toggleCollapsible(\'english-{idx}\')">{HtmlWriter._escape_html(labels.get("english_content", "English Content"))}</button>'
                f'<div class="content active" id="english-{idx}">'
                f'<div class="english-content">{en_content}</div></div>'
            )
        return result or f'<div class="no-content">{HtmlWriter._escape_html(labels.get("no_content", "No displayable content available"))}</div>'

    # ------------------------------------------------------------------

    def get_full_html(self, ans: Answer, get_header: bool = True, lang: str = "en", labels=None) -> str:
        self._labels = labels or {}
        html = self._get_html_start(lang)
        if get_header:
            html += self._get_header(ans)
        html += self._get_references_sections(ans)
        html += self._get_html_end()
        return html

    def _get_html_start(self, lang: str = "en") -> str:
        """HTML start with compact CSS styling"""
        return (
            """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Answer Details</title>
<style>
body { font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin:8px; background:#f5f5f5; direction:ltr; text-align:left; }
"""
            + HtmlWriter.get_container_css()
            + """
.header { background:#2c3e50; color:white; padding:10px 12px; border-radius:5px; margin-bottom:8px; }
.question-label { font-size:0.8em; color:#bdc3c7; margin-bottom:2px; font-weight:normal; }
.question-content { font-size:1.2em; margin:0 0 4px 0; font-weight:bold; }
.timestamp { font-size:0.8em; color:#ecf0f1; margin-bottom:6px; }
.header-info { display:flex; flex-direction:column; gap:4px; font-size:0.85em; }
.info-item { background:rgba(255,255,255,0.1); padding:4px 8px; border-radius:3px; }
.info-label { font-weight:bold; color:#ecf0f1; }
"""
            + HtmlWriter.get_source_section_css()
            + """
[dir="rtl"] .source-title-row, [dir="rtl"] .source-summary-row { flex-direction:row-reverse; }
[dir="rtl"] .collapsible { text-align:right; }
[dir="rtl"] .collapsible::after { right:auto; left:12px; }
</style>
</head>
<body>
<div class="container">"""
        ).replace("<html>", f'<html lang="{self._escape_html(lang)}" dir="{"rtl" if lang.startswith("he") else "ltr"}">').replace("direction:ltr; text-align:left;", "direction:inherit; text-align:start;")

    def _get_header(self, ans: Answer) -> str:
        """Header section with Entities and NERs"""
        entities_str = self._format_list(ans.entities)
        ners_str = self._format_list(ans.rels)
        readable_timestamp = SystemFunctions.get_ts_readable_str(ans.ts)
        return f"""
        <div class="header">
            <div class="question-label">Question:</div>
            <div class="question-content">{ans.free_text_input}</div>
            <div class="timestamp">{readable_timestamp}</div>
            <div class="header-info">
                <div class="info-item"><span class="info-label">Answer Key:</span> {self._escape_html(ans.key)}</div>
                <div class="info-item"><span class="info-label">Entities:</span> {entities_str}</div>
                <div class="info-item"><span class="info-label">NERs:</span> {ners_str}</div>
            </div>
        </div>"""

    def _format_list(self, items: List) -> str:
        if not items:
            return "None"
        return ", ".join(map(str, items))

    def _get_references_sections(self, ans: Answer) -> str:
        html = ""
        for i, src_metadata in enumerate(ans.src_metadata_lst):
            source = ans.src_contents[i] if i < len(ans.src_contents) else None
            html += self._get_reference_section(src_metadata, source, i)
        html += self._get_javascript()
        return html

    def _get_reference_section(self, src_metadata: SourceMetadata, source: SourceContent, index: int) -> str:
        body_id   = f"src-body-{index}"
        header_id = f"src-hdr-{index}"

        title_en    = str(src_metadata)
        title_heb   = src_metadata.to_heb_str()
        summary_en  = getattr(src_metadata, 'summary_en',  None) or ""
        summary_heb = getattr(src_metadata, 'summary_heb', None) or ""

        inner_html = (
            self._get_source_content(source, index)
            if source
            else f'<div class="no-content">{self._escape_html(self._labels.get("no_content", "No source content available"))}</div>'
        )

        return HtmlWriter.build_source_section(
            body_id=body_id,
            header_id=header_id,
            title_en=title_en,
            title_heb=title_heb,
            inner_content_html=inner_html,
            summary_en=summary_en,
            summary_heb=summary_heb,
            passage_types=getattr(src_metadata, 'passage_types', None),
            labels=self._labels,
        )

    def _get_source_content(self, source, index: int) -> str:
        content = source._get_content() if hasattr(source, '_get_content') else getattr(source, 'content', [])
        if not content or len(content) < 2:
            return f'<div class="no-content">{self._escape_html(self._labels.get("no_content", "No content available"))}</div>'
        english_content, hebrew_content = content[0], content[1]
        return HtmlWriter.build_source_content(english_content, hebrew_content, str(index), self._labels)

    def _get_javascript(self) -> str:
        return "<script>\n" + HtmlWriter.get_source_section_js() + "\n</script>"

    def _get_html_end(self) -> str:
        return "</div></body></html>"

    @staticmethod
    def _escape_html(text: str) -> str:
        if not text:
            return ""
        return (str(text).replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;")
                         .replace('"', "&quot;")
                         .replace("'", "&#39;"))
