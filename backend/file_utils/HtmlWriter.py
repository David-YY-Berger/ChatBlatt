from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from system_common import SystemFunctions
from backend.models_db.Answer import Answer
from typing import List

class HtmlWriter:
    def get_full_html(self, ans: Answer, get_header: bool = True) -> str:
        html = self._get_html_start()
        if get_header:
            html += self._get_header(ans)
        html += self._get_references_sections(ans)
        html += self._get_html_end()
        return html

    def _get_html_start(self) -> str:
        """HTML start with compact CSS styling"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Answer Details</title>
<style>
body { font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin:8px; background:#f5f5f5; direction:ltr; text-align:left; }
.container { max-width:1000px; margin:0 auto; background:white; padding:10px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.1); }
.header { background:#2c3e50; color:white; padding:10px 12px; border-radius:5px; margin-bottom:8px; }
.question-label { font-size:0.8em; color:#bdc3c7; margin-bottom:2px; font-weight:normal; }
.question-content { font-size:1.2em; margin:0 0 4px 0; font-weight:bold; }
.timestamp { font-size:0.8em; color:#ecf0f1; margin-bottom:6px; }
.header-info { display:flex; flex-direction:column; gap:4px; font-size:0.85em; }
.info-item { background:rgba(255,255,255,0.1); padding:4px 8px; border-radius:3px; }
.info-label { font-weight:bold; color:#ecf0f1; }
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
.no-content { color:#7f8c8d; font-style:italic; padding:10px; text-align:center; font-size:0.9em; }
</style>
</head>
<body>
<div class="container">"""

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
        body_id = f"src-body-{index}"
        header_id = f"src-hdr-{index}"

        # English and Hebrew toString representations
        title_en = self._escape_html(str(src_metadata))
        title_heb = self._escape_html(src_metadata.to_heb_str())

        # Summary row (EN left, HEB right — on same line)
        summary_en = self._escape_html(getattr(src_metadata, 'summary_en', None) or "")
        summary_heb = self._escape_html(getattr(src_metadata, 'summary_heb', None) or "")
        summary_row_html = ""
        if summary_en or summary_heb:
            summary_row_html = (
                f'<div class="source-summary-row">'
                f'<span class="source-summary-en">{summary_en}</span>'
                f'<span class="source-summary-heb">{summary_heb}</span>'
                f'</div>'
            )

        html = f'<div class="source-section">'
        html += (
            f'<div class="source-header" id="{header_id}" onclick="toggleSource(\'{body_id}\', \'{header_id}\')">'
            f'<div class="source-title-row">'
            f'<span class="source-title-en">{title_en}</span>'
            f'<div class="source-title-right">'
            f'<span class="source-title-heb">{title_heb}</span>'
            f'<span class="source-arrow">▶</span>'
            f'</div>'
            f'</div>'
            f'{summary_row_html}'
            f'</div>'
        )
        html += f'<div class="source-body" id="{body_id}">'
        html += self._get_source_content(source, index) if source else '<div class="no-content">No source content available</div>'
        html += '</div></div>'
        return html

    def _get_source_content(self, source, index: int) -> str:
        content = source._get_content() if hasattr(source, '_get_content') else getattr(source, 'content', [])
        if not content or len(content) < 2:
            return '<div class="no-content">No content available</div>'
        english_content, hebrew_content = content[0], content[1]
        html = ""
        # Content items start open (active) by default
        if hebrew_content.strip():
            html += f'<button class="collapsible active" onclick="toggleCollapsible(\'hebrew-{index}\')">Hebrew Content</button>'
            html += f'<div class="content active" id="hebrew-{index}"><div class="hebrew-content">{hebrew_content}</div></div>'
        if english_content.strip():
            html += f'<button class="collapsible active" onclick="toggleCollapsible(\'english-{index}\')">English Content</button>'
            html += f'<div class="content active" id="english-{index}"><div class="english-content">{english_content}</div></div>'
        return html if html else '<div class="no-content">No displayable content available</div>'

    def _get_javascript(self) -> str:
        return """
<script>
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
}
</script>"""

    def _get_html_end(self) -> str:
        return "</div></body></html>"

    def _escape_html(self, text: str) -> str:
        if not text:
            return ""
        return (str(text).replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;")
                         .replace('"', "&quot;")
                         .replace("'", "&#39;"))
