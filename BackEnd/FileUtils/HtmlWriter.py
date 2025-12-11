from BackEnd.DataObjects.SourceClasses.SourceContent import SourceContent
from BackEnd.General import SystemFunctions
from BackEnd.DataObjects.Answer import Answer
from typing import List

class HtmlWriter:
    def get_ts_readable_str(self, ts: str) -> str:
        """Convert timestamp to readable string"""
        return ts  # Placeholder - replace with actual logic

    def get_full_html(self, ans: Answer) -> str:
        html = self._get_html_start()
        html += self._get_header(ans)
        html += self._get_references_sections(ans)
        html += self._get_html_end()
        return html

    def _get_html_start(self) -> str:
        """HTML start with CSS styling"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Answer Details</title>
<style>
body { font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin:20px; background:#f5f5f5; direction:ltr; text-align:left; }
.container { max-width:1000px; margin:0 auto; background:white; padding:20px; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1); }
.header { background:#2c3e50; color:white; padding:20px; border-radius:6px; margin-bottom:20px; }
.question-label { font-size:0.9em; color:#bdc3c7; margin-bottom:5px; font-weight:normal; }
.question-content { font-size:1.5em; margin:0 0 10px 0; font-weight:bold; }
.timestamp { font-size:0.85em; color:#ecf0f1; margin-bottom:15px; }
.header-info { display:flex; flex-direction:column; gap:10px; font-size:0.9em; }
.info-item { background:rgba(255,255,255,0.1); padding:8px 12px; border-radius:4px; width:100%; }
.info-label { font-weight:bold; color:#ecf0f1; }
.source-section { margin-bottom:30px; border:1px solid #ddd; border-radius:8px; overflow:hidden; }
.source-header { background:#34495e; color:white; padding:15px; font-size:1.1em; font-weight:bold; }
.source-content { padding:20px; background:white; }
.collapsible { background-color:#3498db; color:white; cursor:pointer; padding:12px 15px; width:100%; border:none; text-align:left; outline:none; font-size:14px; border-radius:4px; margin:10px 0 5px 0; transition:all 0.3s ease; position:relative; }
.collapsible:hover { background-color:#2980b9; }
.collapsible.active { background-color:#2ecc71; }
.collapsible::after { content:'▶'; position:absolute; right:15px; top:50%; transform:translateY(-50%); transition:transform 0.3s ease; font-size:14px; }
.collapsible.active::after { content:'▼'; transform:translateY(-50%); }
.content { padding:0; max-height:0; overflow:hidden; transition:max-height 0.3s ease-out; background-color:#f8f9fa; border-radius:0 0 4px 4px; }
.content.active { max-height:2000px; padding:15px; }
.hebrew-content { direction:rtl; text-align:right; font-size:1.1em; line-height:1.8; margin-bottom:15px; padding:15px; background:#fff; border-right:4px solid #e74c3c; border-radius:4px; }
.english-content { direction:ltr; text-align:left; font-size:1.0em; line-height:1.6; margin-bottom:15px; padding:15px; background:#f8f9fa; border-left:4px solid #2ecc71; border-radius:4px; }
.no-content { color:#7f8c8d; font-style:italic; padding:20px; text-align:center; }
</style>
</head>
<body>
<div class="container">"""

    def _get_header(self, ans: Answer) -> str:
        """Header section with Entities and NERs instead of Filters"""
        entities_str = self._format_list(ans.entities)
        ners_str = self._format_list(ans.rels)
        readable_timestamp = SystemFunctions.get_ts_readable_str(ans.ts)

        return f"""
        <div class="header">
            <div class="question-label">Question:</div>
            <div class="question-content">{ans.question_content}</div>
            <div class="timestamp">{readable_timestamp}</div>
            <div class="header-info">
                <div class="info-item">
                    <span class="info-label">Answer Key (in ChatBlatt's Database):</span> {self._escape_html(ans.key)}
                </div>
                <div class="info-item">
                    <span class="info-label">Entities:</span> {entities_str}
                </div>
                <div class="info-item">
                    <span class="info-label">NERs:</span> {ners_str}
                </div>
            </div>
        </div>"""

    def _format_list(self, items: List) -> str:
        """Format list of entities or NERs for display"""
        if not items:
            return "None"
        return ", ".join(map(str, items))

    def _get_references_sections(self, ans: Answer) -> str:
        html = ""
        for i, src_metadata in enumerate(ans.src_metadata_lst):
            source = ans.src_contents[i] if i < len(ans.src_contents) else None
            html += self._get_reference_section(src_metadata.key, source, i)
        html += self._get_javascript()
        return html

    def _get_reference_section(self, ref: str, source: SourceContent, index: int) -> str:
        html = f'<div class="source-section">'
        if source:
            header = source.to_string() if hasattr(source, 'to_string') else str(source)
            html += f'<div class="source-header">Source {index+1}: {self._escape_html(header)}</div>'
        else:
            html += f'<div class="source-header">Source {index+1}: {self._escape_html(ref)}</div>'
        html += '<div class="source-content">'
        html += self._get_source_content(source, index) if source else '<div class="no-content">No source content available</div>'
        html += '</div></div>'
        return html

    def _get_source_content(self, source, index: int) -> str:
        content = source._get_content() if hasattr(source, 'get_content') else getattr(source, 'content', [])
        if not content or len(content) < 2:
            return '<div class="no-content">No content available</div>'
        english_content, hebrew_content = content[0], content[1]
        html = ""
        if hebrew_content.strip():
            html += f'<button class="collapsible" onclick="toggleCollapsible(\'hebrew-{index}\')">Hebrew Content</button>'
            html += f'<div class="content" id="hebrew-{index}"><div class="hebrew-content">{hebrew_content}</div></div>'
        if english_content.strip():
            html += f'<button class="collapsible" onclick="toggleCollapsible(\'english-{index}\')">English Content</button>'
            html += f'<div class="content" id="english-{index}"><div class="english-content">{english_content}</div></div>'
        return html if html else '<div class="no-content">No displayable content available</div>'

    def _get_javascript(self) -> str:
        return """
<script>
function toggleCollapsible(contentId) {
    var content = document.getElementById(contentId);
    var button = content.previousElementSibling;
    if (content.classList.contains('active')) {
        content.classList.remove('active');
        button.classList.remove('active');
    } else {
        content.classList.add('active');
        button.classList.add('active');
    }
}
</script>"""

    def _get_html_end(self) -> str:
        return "</div></body></html>"

    def _escape_html(self, text: str) -> str:
        if not text:
            return ""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;"))
