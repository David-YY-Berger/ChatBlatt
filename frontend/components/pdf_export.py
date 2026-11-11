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
from backend.models_db.Enums import SourceType
from translations1 import enum_text, get_text, is_rtl

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
    pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(FRONTEND_DIR / "fonts" / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-BoldOblique", str(FRONTEND_DIR / "fonts" / "DejaVuSans-BoldOblique.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD,
                                  italic="DejaVu-Oblique", boldItalic="DejaVu-BoldOblique")


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

    for key, label in (("st", "Source types"), ("pt", "Passage types")):
        values = [value.strip() for value in params.get(key, [""])[0].split(",") if value.strip()]
        if not values:
            continue
        if key == "st":
            values = [
                SourceType[value].value if value in SourceType.__members__ else value
                for value in values
            ]
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
                 dedication: str = "", lang: str = "en"):
        super().__init__()
        self.width, self.height, self.stamp = width, 3.2 * cm, stamp
        self.search_url = search_url
        self.dedication = dedication
        self.lang = lang

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(_NAVY)
        c.roundRect(0, 0, self.width, self.height, 8, stroke=0, fill=1)
        pad, side = 0.3 * cm, self.height - 0.6 * cm
        rtl = is_rtl(self.lang)
        image_x = self.width - pad - side if rtl else pad
        if MAIN_IMAGE.exists():
            c.drawImage(str(MAIN_IMAGE), image_x, pad, side, side, preserveAspectRatio=True, mask="auto")
            c.linkURL(Paths.EITZ_HABINA_URL, (image_x, pad, image_x + side, pad + side), relative=1)
        x = image_x - 0.6 * cm if rtl else pad + side + 0.6 * cm
        draw_text = c.drawRightString if rtl else c.drawString
        def display(text):
            return get_display(text, base_dir="R") if rtl else text
        c.setFillColor(colors.white)
        c.setFont(FONT_BOLD, 26)
        draw_text(x, self.height - 1.4 * cm, display(get_text("app.title", self.lang)))
        if self.dedication:
            c.setFont(FONT, 8)
            dedication = get_display(self.dedication, base_dir="R") if _HEB_RE.search(self.dedication) else self.dedication
            draw_text(x, self.height - 0.62 * cm, dedication)
        c.setFont(FONT, 8)
        bsad = get_display("בס״ד", base_dir="R")
        (c.drawString if rtl else c.drawRightString)(pad if rtl else self.width - pad, self.height - 0.4 * cm, bsad)
        c.setFont(FONT, 9)
        c.setFillColor(colors.HexColor("#ecf0f1"))
        draw_text(x, 0.9 * cm, display(f"{get_text('source_display.downloaded', self.lang)}: {self.stamp}"))
        if self.search_url:
            label = display(get_text("source_display.open_search", self.lang))
            c.setFillColor(colors.HexColor("#8ecbff"))
            c.setFont(FONT_BOLD, 10)
            draw_text(x, 1.35 * cm, label)
            label_width = pdfmetrics.stringWidth(label, FONT_BOLD, 10)
            c.linkURL(self.search_url, (x - label_width if rtl else x, 1.25 * cm, x if rtl else x + label_width, 1.65 * cm),
                      relative=1)


_BOLD_TAGS = {"b", "strong", "h1", "h2", "h3", "h4", "h5", "h6", "th"}
_ITALIC_TAGS = {"i", "em", "cite", "dfn"}
_Run = tuple[str, bool, bool]  # (text, bold, italic)


def _html_runs(html: str) -> list[_Run]:
    """HTML fragment -> styled text runs (bold/italic preserved, <br> as newline)."""
    runs: list[_Run] = []

    def walk(node, bold, italic):
        for child in node.children:
            if child.name is None:
                text = str(child)
                if text:
                    runs.append((text, bold, italic))
            elif child.name == "br":
                runs.append(("\n", bold, italic))
            elif child.name in ("script", "style"):
                continue
            else:
                walk(child, bold or child.name in _BOLD_TAGS, italic or child.name in _ITALIC_TAGS)

    walk(BeautifulSoup(html or "", "html.parser"), False, False)
    return runs


def _markup(word: str, bold: bool, italic: bool) -> str:
    out = escape(word)
    # DejaVu Oblique has no Hebrew glyphs, so Hebrew stays upright
    if italic and not _HEB_RE.search(word):
        out = f"<i>{out}</i>"
    if bold:
        out = f"<b>{out}</b>"
    return out


def _rtl_line_markup(words: list[tuple[str, bool, bool]]) -> str:
    """Visual-order markup for one line: Hebrew words are bidi-reversed, and runs
    of purely LTR words keep their internal order within the reversed line."""
    units: list[list[str]] = []
    prev_ltr = False
    for word, bold, italic in words:
        ltr = not _HEB_RE.search(word) and bool(re.search(r"[A-Za-z0-9]", word))
        shown = word if ltr else get_display(word, base_dir="R")
        piece = _markup(shown, bold, italic)
        if ltr and prev_ltr:
            units[-1].append(piece)
        else:
            units.append([piece])
        prev_ltr = ltr
    return " ".join(" ".join(unit) for unit in reversed(units))


def _tokenize(runs: list[_Run]) -> list[tuple[str, bool, bool] | None]:
    """Split runs into styled words; None marks a newline."""
    tokens: list = []
    for text, bold, italic in runs:
        for part in re.split(r"(\n)", text):
            if part == "\n":
                tokens.append(None)
            else:
                tokens += [(w, bold, italic) for w in part.split()]
    return tokens


def _text_flowables(text: str, size: float, width: float, bold=False, italic_color=None,
                    leading=None, html: bool = False) -> list:
    """Paragraphs for a (possibly Hebrew) text block, one per visual line for RTL.
    With ``html=True`` the text is an HTML fragment whose bold/italic is kept."""
    if not text:
        return []
    runs = _html_runs(text) if html else [(text, False, False)]
    tokens = _tokenize(runs)
    leading = leading or size * 1.45
    color = italic_color or colors.HexColor("#1a1a1a")
    wrap_bold = bold
    if any(t and _HEB_RE.search(t[0]) for t in tokens):
        style = ParagraphStyle("h", fontName=FONT, fontSize=size, leading=leading,
                               alignment=TA_RIGHT, textColor=color)
        lines: list[list] = []
        cur: list = []
        cur_text = ""
        for tok in tokens:
            if tok is None:
                lines.append(cur)
                cur, cur_text = [], ""
                continue
            font = FONT_BOLD if (wrap_bold or tok[1]) else FONT
            cand = f"{cur_text} {tok[0]}" if cur_text else tok[0]
            if cur and pdfmetrics.stringWidth(cand, font, size) > width:
                lines.append(cur)
                cur, cur_text = [tok], tok[0]
            else:
                cur.append(tok)
                cur_text = cand
        lines.append(cur)
        out = []
        for line in lines:
            markup = _rtl_line_markup([(w, b or wrap_bold, i) for w, b, i in line])
            out.append(Paragraph(markup or "&nbsp;", style))
        return out

    style = ParagraphStyle("e", fontName=FONT, fontSize=size, leading=leading,
                           alignment=TA_LEFT, textColor=color)
    paragraphs: list[str] = []
    cur_words: list[str] = []
    newlines = 0
    for tok in tokens + [None]:
        if tok is None:
            newlines += 1
            continue
        if newlines >= 2 and cur_words:
            paragraphs.append(" ".join(cur_words))
            cur_words = []
        elif newlines == 1 and cur_words:
            cur_words.append("<br/>")
        newlines = 0
        cur_words.append(_markup(tok[0], tok[1] or wrap_bold, tok[2]))
    if cur_words:
        paragraphs.append(" ".join(cur_words))
    return [Paragraph(p.replace(" <br/> ", "<br/>"), style) for p in paragraphs]


def build_results_pdf(ans, search_url: str | None = None, entity_names: list[str] | None = None,
                      dedication: str = "", lang: str = "en") -> bytes:
    """Build the result PDF in the selected UI language."""
    _register_fonts()
    buf = io.BytesIO()
    margin = 1.8 * cm
    description = _search_description(search_url, entity_names)
    base_title = f"{get_text('app.title', lang)} - {get_text('source_display.sources', lang)}"
    title = f"{base_title} - {description}" if description else base_title
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin, title=title,
                            author="Eitz Habina")
    width = A4[0] - 2 * margin
    inner = width - 0.8 * cm
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    story: list = [_Header(width, stamp, search_url, dedication, lang), Spacer(1, 0.4 * cm)]
    sources = list(getattr(ans, "src_metadata_lst", []) or [])
    contents = list(getattr(ans, "src_contents", []) or [])
    story += _text_flowables(f"{len(sources)} {get_text('source_display.sources', lang)}", 10, inner)
    story += [Spacer(1, 0.2 * cm)]
    story.append(Spacer(1, 0.3 * cm))

    for i, meta in enumerate(sources):
        src = contents[i] if i < len(contents) else None
        block: list = []
        title_style = ParagraphStyle("t", fontName=FONT_BOLD, fontSize=12, leading=16,
                                     textColor=colors.white, backColor=_NAVY,
                                     borderPadding=(5, 6, 5, 6), spaceAfter=8)
        heb_title = _plain(meta.to_heb_str()) if hasattr(meta, "to_heb_str") else ""
        primary_title = heb_title if is_rtl(lang) and heb_title else str(meta)
        secondary_title = str(meta) if is_rtl(lang) and heb_title else heb_title
        if is_rtl(lang):
            title_style.alignment = TA_RIGHT
        block.append(Paragraph(escape(get_display(f"{i + 1}. {primary_title}", base_dir="R") if is_rtl(lang) else f"{i + 1}. {primary_title}"), title_style))
        block += _text_flowables(secondary_title, 12, inner, bold=True)
        types = ", ".join(enum_text(pt, lang) for pt in (getattr(meta, "passage_types", None) or []))
        grey = colors.HexColor("#7f8c8d")
        if types:
            block += _text_flowables(types, 9, inner, italic_color=grey)
        for summ in (getattr(meta, "summary_en", None), getattr(meta, "summary_heb", None)):
            block += _text_flowables(summ or "", 9, inner, italic_color=grey, html=True)
        block.append(Spacer(1, 0.2 * cm))

        content = []
        if src is not None:
            content = src._get_content() if hasattr(src, "_get_content") else getattr(src, "content", [])
        if content and len(content) >= 2:
            heb, eng = content[1] or "", content[0] or ""
        else:
            heb = eng = ""
        body = _text_flowables(heb, 11, inner, leading=17, html=True)
        if heb and eng:
            body.append(Spacer(1, 0.3 * cm))
        body += _text_flowables(eng, 10, inner, leading=14.5, html=True)
        if not body:
            body = _text_flowables(get_text("source_display.no_content", lang), 9, inner, italic_color=grey)

        story.append(KeepTogether(block + body[:3]))
        story += body[3:]
        story.append(Spacer(1, 0.7 * cm))

    def _footer(canvas, d):
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.grey)
        footer = f"{get_text('app.title', lang)}  |  {stamp}  |  {get_text('source_display.page', lang)} {d.page}"
        canvas.drawCentredString(A4[0] / 2, 0.9 * cm, get_display(footer, base_dir="R") if is_rtl(lang) else footer)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
