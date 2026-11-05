# bs"d - lehagdil torah velahadir
"""Builds a formatted PDF of source-search results (see pages/source_search.py)."""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape

from bidi.algorithm import get_display
from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from backend.common import Paths

FRONTEND_DIR = Path(__file__).resolve().parent.parent
MAIN_IMAGE = FRONTEND_DIR / "icons" / "optimized" / "eitz_habina_main_image.jpg"
FONT = "DejaVu"
FONT_BOLD = "DejaVu-Bold"
_HEB_RE = re.compile(r"[\u0590-\u05FF]")
_NAVY = colors.HexColor("#2c3e50")


def _register_fonts() -> None:
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(FONT, str(FRONTEND_DIR / "fonts" / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FRONTEND_DIR / "fonts" / "DejaVuSans-Bold.ttf")))


def _plain(html: str) -> str:
    """HTML fragment -> plain text with paragraph breaks preserved."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text()
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _search_description(search_url: str | None, entity_names: list[str] | None = None) -> str:
    """Return a short, readable summary of the search parameters."""
    descriptions = []
    params = parse_qs(urlsplit(search_url).query) if search_url else {}
    if entity_names:
        descriptions.append(f"Entity: {', '.join(entity_names[:2])}"
                            + (", ..." if len(entity_names) > 2 else ""))

    fields = [
        ("q", "Search"),
        ("rel_label", "Relationship"),
    ]
    for key, label in fields:
        values = [value.strip() for value in params.get(key, [""])[0].split(",") if value.strip()]
        if not values:
            continue
        shown = values[:2]
        text = ", ".join(shown)
        if len(values) > len(shown):
            text += ", ..."
        descriptions.append(f"{label}: {text}")

    for key, label in (("books", "Books"), ("pt", "Passage types")):
        values = [value.strip() for value in params.get(key, [""])[0].split(",") if value.strip()]
        if not values:
            continue
        shown = values[:2]
        text = ", ".join(shown)
        if len(values) > len(shown):
            text += ", ..."
        descriptions.append(f"{label}: {text}")

    description = " | ".join(descriptions)
    if len(description) > 110:
        description = description[:107].rsplit(" ", 1)[0].rstrip(" ,|") + "..."
    return description


def results_pdf_filename(search_url: str | None, entity_names: list[str] | None = None) -> str:
    """Build a filesystem-safe download name containing a concise search summary."""
    description = _search_description(search_url, entity_names) or "All sources"
    slug = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", description)
    slug = re.sub(r"[\s_-]+", "_", slug).strip(" ._")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"eitz_habina_sources_{slug}_{stamp}.pdf"


def _wrap(text: str, font: str, size: float, width: float) -> list[str]:
    """Greedy word wrap in logical order (needed so bidi can be applied per line)."""
    lines: list[str] = []
    for raw in text.split("\n"):
        cur = ""
        for word in raw.split():
            cand = f"{cur} {word}" if cur else word
            if cur and pdfmetrics.stringWidth(cand, font, size) > width:
                lines.append(cur)
                cur = word
            else:
                cur = cand
        lines.append(cur)
    return lines


class _Header(Flowable):
    """Banner with the main picture (clickable) and the 'eitz habina' title."""

    def __init__(self, width: float, stamp: str, search_url: str | None = None,
                 dedication: str = ""):
        super().__init__()
        self.width, self.height, self.stamp = width, 3.2 * cm, stamp
        self.search_url = search_url
        self.dedication = dedication

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(_NAVY)
        c.roundRect(0, 0, self.width, self.height, 8, stroke=0, fill=1)
        pad, side = 0.3 * cm, self.height - 0.6 * cm
        if MAIN_IMAGE.exists():
            c.drawImage(str(MAIN_IMAGE), pad, pad, side, side, preserveAspectRatio=True, mask="auto")
            c.linkURL(Paths.EITZ_HABINA_URL, (pad, pad, pad + side, pad + side), relative=1)
        x = pad + side + 0.6 * cm
        c.setFillColor(colors.white)
        c.setFont(FONT_BOLD, 26)
        c.drawString(x, self.height - 1.4 * cm, "Eitz Habina")
        if self.dedication:
            c.setFont(FONT, 8)
            dedication = get_display(self.dedication, base_dir="R") if _HEB_RE.search(self.dedication) else self.dedication
            c.drawString(x, self.height - 0.62 * cm, dedication)
        c.setFont(FONT, 8)
        bsad = get_display("בס״ד", base_dir="R")
        c.drawRightString(self.width - pad, self.height - 0.4 * cm, bsad)
        c.setFont(FONT, 9)
        c.setFillColor(colors.HexColor("#ecf0f1"))
        c.drawString(x, 0.9 * cm, f"Downloaded: {self.stamp}")
        c.drawString(x, 0.45 * cm, Paths.EITZ_HABINA_URL)
        if self.search_url:
            label = "Open this search online"
            c.setFillColor(colors.HexColor("#8ecbff"))
            c.setFont(FONT_BOLD, 10)
            c.drawString(x, 1.35 * cm, label)
            c.linkURL(self.search_url, (x, 1.25 * cm, x + pdfmetrics.stringWidth(label, FONT_BOLD, 10), 1.65 * cm),
                      relative=1)


def _text_flowables(text: str, size: float, width: float, bold=False, italic_color=None,
                    leading=None) -> list:
    """Paragraphs for a (possibly Hebrew) text block, one per visual line for RTL."""
    if not text:
        return []
    font = FONT_BOLD if bold else FONT
    leading = leading or size * 1.45
    color = italic_color or colors.HexColor("#1a1a1a")
    if _HEB_RE.search(text):
        style = ParagraphStyle("h", fontName=font, fontSize=size, leading=leading,
                               alignment=TA_RIGHT, textColor=color)
        return [Paragraph(escape(get_display(line, base_dir="R")) or "&nbsp;", style)
                for line in _wrap(text, font, size, width)]
    style = ParagraphStyle("e", fontName=font, fontSize=size, leading=leading,
                           alignment=TA_LEFT, textColor=color)
    return [Paragraph(escape(p).replace("\n", "<br/>"), style) for p in text.split("\n\n") if p.strip()]


def build_results_pdf(ans, search_url: str | None = None, entity_names: list[str] | None = None,
                      dedication: str = "") -> bytes:
    """Build the result PDF, including selected English entity names and localized dedication."""
    _register_fonts()
    buf = io.BytesIO()
    margin = 1.8 * cm
    description = _search_description(search_url, entity_names)
    title = f"Eitz Habina Sources - {description}" if description else "Eitz Habina Sources"
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin, title=title,
                            author="Eitz Habina")
    width = A4[0] - 2 * margin
    inner = width - 0.8 * cm
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    story: list = [_Header(width, stamp, search_url, dedication), Spacer(1, 0.4 * cm)]
    sources = list(getattr(ans, "src_metadata_lst", []) or [])
    contents = list(getattr(ans, "src_contents", []) or [])
    count_style = ParagraphStyle("c", fontName=FONT, fontSize=10, textColor=colors.HexColor("#555555"))
    story += [Paragraph(f"{len(sources)} sources", count_style), Spacer(1, 0.2 * cm)]
    if search_url:
        link_style = ParagraphStyle("l", fontName=FONT, fontSize=7, leading=9, wordWrap="CJK",
                                    textColor=colors.HexColor("#1a5fb4"))
        story.append(Paragraph(f'Search link: <link href="{escape(search_url, {chr(34): "&quot;"})}">{escape(search_url)}</link>', link_style))
    story.append(Spacer(1, 0.3 * cm))

    for i, meta in enumerate(sources):
        src = contents[i] if i < len(contents) else None
        block: list = []
        title_style = ParagraphStyle("t", fontName=FONT_BOLD, fontSize=12, leading=16,
                                     textColor=colors.white, backColor=_NAVY,
                                     borderPadding=(5, 6, 5, 6), spaceAfter=8)
        block.append(Paragraph(f"{i + 1}. {escape(str(meta))}", title_style))
        heb_title = _plain(meta.to_heb_str()) if hasattr(meta, "to_heb_str") else ""
        block += _text_flowables(heb_title, 12, inner, bold=True)
        types = ", ".join(str(getattr(pt, "value", pt)) for pt in (getattr(meta, "passage_types", None) or []))
        grey = colors.HexColor("#7f8c8d")
        if types:
            block += _text_flowables(types, 9, inner, italic_color=grey)
        for summ in (getattr(meta, "summary_en", None), getattr(meta, "summary_heb", None)):
            block += _text_flowables(_plain(summ or ""), 9, inner, italic_color=grey)
        block.append(Spacer(1, 0.2 * cm))

        content = []
        if src is not None:
            content = src._get_content() if hasattr(src, "_get_content") else getattr(src, "content", [])
        if content and len(content) >= 2:
            heb, eng = _plain(content[1]), _plain(content[0])
        else:
            heb = eng = ""
        body = _text_flowables(heb, 11, inner, leading=17)
        if heb and eng:
            body.append(Spacer(1, 0.3 * cm))
        body += _text_flowables(eng, 10, inner, leading=14.5)
        if not body:
            body = _text_flowables("No content available", 9, inner, italic_color=grey)

        story.append(KeepTogether(block + body[:3]))
        story += body[3:]
        story.append(Spacer(1, 0.7 * cm))

    def _footer(canvas, d):
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(A4[0] / 2, 0.9 * cm, f"Eitz Habina  |  {stamp}  |  Page {d.page}")

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
