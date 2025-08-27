from BackEnd.General import SystemFunctions
from BackEnd.Main.Answer import Answer
from typing import List


class HtmlWriter:
    def get_ts_readable_str(self, ts: str) -> str:
        """Convert timestamp to readable string - implement based on your timestamp format"""
        # Add your timestamp conversion logic here
        # This is a placeholder - replace with actual implementation
        return ts

    def get_full_html(self, ans: Answer) -> str:
        """Generate complete HTML document for an Answer object"""
        html = self._get_html_start()
        html += self._get_header(ans)
        html += self._get_references_sections(ans)
        html += self._get_html_end()
        return html

    def _get_html_start(self) -> str:
        """Generate HTML document start with CSS styling"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Answer Details</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
            direction: ltr;
            text-align: left;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .question-label {
            font-size: 0.9em;
            color: #bdc3c7;
            margin-bottom: 5px;
            font-weight: normal;
        }
        .question-content {
            font-size: 1.5em;
            margin: 0 0 10px 0;
            font-weight: bold;
        }
        .timestamp {
            font-size: 0.85em;
            color: #ecf0f1;
            margin-bottom: 15px;
        }
        .header-info {
            display: flex;
            flex-direction: column;
            gap: 10px;
            font-size: 0.9em;
        }
        .info-item {
            background: rgba(255,255,255,0.1);
            padding: 8px 12px;
            border-radius: 4px;
            width: 100%;
        }
        .info-label {
            font-weight: bold;
            color: #ecf0f1;
        }
        .source-section {
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .source-header {
            background: #34495e;
            color: white;
            padding: 15px;
            font-size: 1.1em;
            font-weight: bold;
        }
        .source-content {
            padding: 20px;
            background: white;
        }
        .collapsible {
            background-color: #3498db;
            color: white;
            cursor: pointer;
            padding: 12px 15px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 14px;
            border-radius: 4px;
            margin: 10px 0 5px 0;
            transition: all 0.3s ease;
            position: relative;
        }
        .collapsible:hover {
            background-color: #2980b9;
        }
        .collapsible.active {
            background-color: #2ecc71;
        }
        .collapsible::after {
            content: '▶';
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            transition: transform 0.3s ease;
            font-size: 14px;
        }
        .collapsible.active::after {
            content: '▼';
            transform: translateY(-50%);
        }
        .content {
            padding: 0;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background-color: #f8f9fa;
            border-radius: 0 0 4px 4px;
        }
        .content.active {
            max-height: 2000px;
            padding: 15px;
        }
        .hebrew-content {
            direction: rtl;
            text-align: right;
            font-size: 1.1em;
            line-height: 1.8;
            margin-bottom: 15px;
            padding: 15px;
            background: #fff;
            border-right: 4px solid #e74c3c;
            border-radius: 4px;
        }
        .english-content {
            direction: ltr;
            text-align: left;
            font-size: 1.0em;
            line-height: 1.6;
            margin-bottom: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #2ecc71;
            border-radius: 4px;
        }
        .no-content {
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">"""

    def _get_header(self, ans: Answer) -> str:
        """Generate header section with answer metadata"""
        filters_str = self._format_filters(ans.filters)
        readable_timestamp = SystemFunctions.get_ts_readable_str(ans.ts)

        return f"""
        <div class="header">
            <div class="question-label">Question:</div>
            <div class="question-content">{ans.question}</div>
            <div class="timestamp">{readable_timestamp}</div>
            <div class="header-info">
                <div class="info-item">
                    <span class="info-label">Answer Key (in ChatBlatt's Database):</span> {self._escape_html(ans.key)}
                </div>
                <div class="info-item">
                    <span class="info-label">Filters:</span> {filters_str}
                </div>
            </div>
        </div>"""

    def _get_references_sections(self, ans: Answer) -> str:
        """Generate sections for each reference with their sources"""
        html = ""

        for i, ref in enumerate(ans.refs):
            # Find corresponding source
            source = None
            if i < len(ans.srcs):
                source = ans.srcs[i]

            html += self._get_reference_section(ref, source, i)

        # Add JavaScript for collapsible functionality
        html += self._get_javascript()

        return html

    def _get_reference_section(self, ref: str, source, index: int) -> str:
        """Generate a single reference section with source content"""
        html = f"""
        <div class="source-section">"""

        # Source header with source.to_string()
        if source is not None:
            source_header = source.to_string() if hasattr(source, 'to_string') else str(source)
            html += f"""
            <div class="source-header">
                Source {index + 1}: {self._escape_html(source_header)}
            </div>"""
        else:
            html += f"""
            <div class="source-header">
                Source {index + 1}: {self._escape_html(ref)}
            </div>"""

        html += """
            <div class="source-content">"""

        if source is not None:
            html += self._get_source_content(source, index)
        else:
            html += '<div class="no-content">No source content available</div>'

        html += """
            </div>
        </div>"""

        return html

    def _get_source_content(self, source, index: int) -> str:
        """Generate source content with collapsible Hebrew and English sections"""
        html = ""

        # Get content using getter method
        content = source.get_content() if hasattr(source, 'get_content') else getattr(source, 'content', [])

        if not content or len(content) < 2:
            return '<div class="no-content">No content available</div>'

        # Assuming index 0 = English, 1 = Hebrew, 2 = English_clean (skip)
        english_content = content[0] if len(content) > 0 else ""
        hebrew_content = content[1] if len(content) > 1 else ""

        # Hebrew content section (collapsible) - shown first
        if hebrew_content and hebrew_content.strip():
            html += f"""
            <button class="collapsible" onclick="toggleCollapsible('hebrew-{index}')">
                Hebrew Content
            </button>
            <div class="content" id="hebrew-{index}">
                <div class="hebrew-content">{hebrew_content}</div>
            </div>"""

        # English content section (collapsible)
        if english_content and english_content.strip():
            html += f"""
            <button class="collapsible" onclick="toggleCollapsible('english-{index}')">
                English Content
            </button>
            <div class="content" id="english-{index}">
                <div class="english-content">{english_content}</div>
            </div>"""

        if not html:
            html = '<div class="no-content">No displayable content available</div>'

        return html

    def _get_javascript(self) -> str:
        """Generate JavaScript for collapsible functionality"""
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
        """Generate HTML document end"""
        return """
    </div>
</body>
</html>"""

    def _format_filters(self, filters: List[List[int]]) -> str:
        """Format filters for display"""
        if not filters:
            return "None"

        formatted = []
        for filter_group in filters:
            # Check if filter_group is None or empty
            if filter_group is None:
                formatted.append("[]")
            elif not filter_group:
                formatted.append("[]")
            else:
                formatted.append(f"[{', '.join(map(str, filter_group))}]")

        return ", ".join(formatted)

    def _is_hebrew(self, text: str) -> bool:
        """Check if text contains Hebrew characters"""
        # Remove HTML tags for better detection
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)

        hebrew_chars = 0
        total_chars = 0

        for char in clean_text:
            if char.strip() and not char.isspace():
                total_chars += 1
                if '\u0590' <= char <= '\u05FF':  # Hebrew Unicode range
                    hebrew_chars += 1

        return total_chars > 0 and (hebrew_chars / total_chars) > 0.3

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""

        return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))