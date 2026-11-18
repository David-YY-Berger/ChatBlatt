# bs"d - lehagdil torah velahadir
"""Builds a formatted PDF of source-search results (see pages/source_search.py)."""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
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
from backend.models_db.Enums import PassageType, SourceType
from translations1 import enum_text, get_text, is_rtl

FRONTEND_DIR = Path(__file__).resolve().parent.parent
MAIN_IMAGE = FRONTEND_DIR / "icons" / "optimized" / "eitz_habina_main_image.jpg"
FONT = "DejaVu"
FONT_BOLD = "DejaVu-Bold"
HEBREW_FONT = "FreeSerif"
HEBREW_FONT_BOLD = "FreeSerif-Bold"
_HEB_RE = re.compile(r"[\u0590-\u05FF]")
_NAVY = colors.HexColor("#2c3e50")
_PDF_LOCK = Lock()


def _register_fonts() -> None:
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(FONT, str(FRONTEND_DIR / "fonts" / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FRONTEND_DIR / "fonts" / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(FRONTEND_DIR / "fonts" / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-BoldOblique", str(FRONTEND_DIR / "fonts" / "DejaVuSans-BoldOblique.ttf")))
    pdfmetrics.registerFont(TTFont(HEBREW_FONT, str(FRONTEND_DIR / "fonts" / "FreeSerif.ttf")))
    pdfmetrics.registerFont(TTFont(HEBREW_FONT_BOLD, str(FRONTEND_DIR / "fonts" / "FreeSerifBold.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD,
                                  italic="DejaVu-Oblique", boldItalic="DejaVu-BoldOblique")
    pdfmetrics.registerFontFamily(HEBREW_FONT, normal=HEBREW_FONT, bold=HEBREW_FONT_BOLD,
                                  italic=HEBREW_FONT, boldItalic=HEBREW_FONT_BOLD)


def _plain(html: str) -> str:
    """HTML fragment -> plain text with paragraph breaks preserved."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
        block.insert_after("\n")
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


def _bilingual_text(key: str, lang: str) -> str:
    labels = [get_text(key, code) for code in ("en", "he")]
    if is_rtl(lang):
        labels.reverse()
    return " / ".join(labels)


def _search_parameter_rows(
    search_url: str | None, entity_names: list[str] | None, lang: str,
) -> list[tuple[str, str]]:
    """Return all executed source-search settings with bilingual labels/values."""
    params = parse_qs(urlsplit(search_url).query) if search_url else {}

    def values(key: str) -> list[str]:
        return [value.strip() for value in params.get(key, [""])[0].split(",") if value.strip()]

    query = params.get("q", [""])[0].strip()
    rows = [(
        _bilingual_text("source_display.pdf_text_query", lang),
        query or _bilingual_text("source_display.pdf_none", lang),
    )]

    entities = list(entity_names or [])
    if not entities:
        entities = values("ent")
    rows.append((
        _bilingual_text("source_display.pdf_entities", lang),
        ", ".join(entities) if entities else _bilingual_text("source_display.pdf_all_entities", lang),
    ))

    relationship = params.get("rel_label", [""])[0].strip()
    if not relationship:
        relationship = ", ".join(values("rel"))
    rows.append((
        _bilingual_text("source_display.pdf_relationship", lang),
        relationship or _bilingual_text("source_display.pdf_none", lang),
    ))

    for key, enum_type, label_key in (
        ("st", SourceType, "source_display.pdf_source_types"),
        ("pt", PassageType, "source_display.pdf_passage_types"),
    ):
        selected = values(key)
        rendered = []
        for value in selected:
            member = enum_type.__members__.get(value)
            rendered.append(_bilingual_text_enum(member, lang) if member else value)
        rows.append((
            _bilingual_text(label_key, lang),
            ", ".join(rendered) if rendered else _bilingual_text("source_display.pdf_all_types", lang),
        ))

    if values("ent"):
        match_all = params.get("entity_match", ["any"])[0] == "all"
        match_key = "source_display.pdf_match_all" if match_all else "source_display.pdf_match_any"
        rows.append((_bilingual_text("source_display.pdf_entity_match", lang),
                     _bilingual_text(match_key, lang)))
    return rows


def _bilingual_text_enum(member: SourceType | PassageType, lang: str) -> str:
    return f"{enum_text(member, 'en')} / {enum_text(member, 'he')}" if not is_rtl(lang) else (
        f"{enum_text(member, 'he')} / {enum_text(member, 'en')}"
    )


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


class _SefariaLink(Flowable):
    """A compact, clickable book-icon link to a source's Sefaria page."""

    def __init__(self, url: str, label: str, lang: str = "en"):
        super().__init__()
        self.url = url
        self.label = label
        self.lang = lang
        self.width = 5 * cm
        self.height = 0.55 * cm

    def wrap(self, available_width, _):
        self.width = min(self.width, available_width)
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        color = colors.HexColor("#1d6fa4")
        c.setStrokeColor(color)
        c.setFillColor(color)
        icon_w, gap = 0.32 * cm, 0.12 * cm
        display_label = get_display(self.label, base_dir="R") if is_rtl(self.lang) else self.label
        text_width = pdfmetrics.stringWidth(display_label, FONT, 9)
        total_width = icon_w + gap + text_width
        if is_rtl(self.lang):
            icon_x = self.width - icon_w
            text_x = icon_x - gap
            c.drawRightString(text_x, 0.08 * cm, display_label)
            c.line(text_x - text_width, 0.06 * cm, text_x, 0.06 * cm)
        else:
            icon_x = 0
            text_x = icon_x + icon_w + gap
            c.drawString(text_x, 0.08 * cm, display_label)
            c.line(text_x, 0.06 * cm, text_x + text_width, 0.06 * cm)

        mid = icon_x + icon_w / 2
        path = c.beginPath()
        path.moveTo(mid, 0.04 * cm)
        path.curveTo(mid - 0.04 * cm, 0.13 * cm, icon_x, 0.11 * cm, icon_x, 0.16 * cm)
        path.lineTo(icon_x, 0.48 * cm)
        path.curveTo(icon_x + 0.12 * cm, 0.43 * cm, mid - 0.04 * cm, 0.45 * cm, mid, 0.52 * cm)
        path.curveTo(mid + 0.04 * cm, 0.45 * cm, icon_x + icon_w - 0.12 * cm, 0.43 * cm,
                     icon_x + icon_w, 0.48 * cm)
        path.lineTo(icon_x + icon_w, 0.16 * cm)
        path.curveTo(icon_x + icon_w, 0.11 * cm, mid + 0.04 * cm, 0.13 * cm, mid, 0.04 * cm)
        c.drawPath(path, stroke=1, fill=0)
        c.line(mid, 0.07 * cm, mid, 0.45 * cm)
        c.linkURL(self.url, (0, 0, self.width, self.height), relative=1)
        c.restoreState()


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
    # Hebrew stays upright; the Hebrew font has no italic variant.
    if italic and not _HEB_RE.search(word):
        out = f"<i>{out}</i>"
    if bold:
        out = f"<b>{out}</b>"
    return out


def _rtl_line_markup(words: list[tuple[str, bool, bool]]) -> str:
    """Order words visually; shaping handles Hebrew letters and their marks."""
    units: list[list[str]] = []
    prev_ltr = False
    for word, bold, italic in words:
        ltr = not _HEB_RE.search(word) and bool(re.search(r"[A-Za-z0-9]", word))
        if _HEB_RE.search(word):
            font = HEBREW_FONT_BOLD if bold else HEBREW_FONT
            piece = f'<font name="{font}">{escape(word)}</font>'
        else:
            piece = _markup(word if ltr else get_display(word, base_dir="R"), bold, italic)
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
                               alignment=TA_RIGHT, textColor=color, shaping=1)
        lines: list[list] = []
        cur: list = []
        cur_width = 0.0
        for tok in tokens:
            if tok is None:
                lines.append(cur)
                cur, cur_width = [], 0.0
                continue
            is_bold = wrap_bold or tok[1]
            if _HEB_RE.search(tok[0]):
                font = HEBREW_FONT_BOLD if is_bold else HEBREW_FONT
            else:
                font = FONT_BOLD if is_bold else FONT
            word_width = pdfmetrics.stringWidth(tok[0], font, size)
            space_width = pdfmetrics.stringWidth(" ", FONT, size) if cur else 0
            if cur and cur_width + space_width + word_width > width:
                lines.append(cur)
                cur, cur_width = [tok], word_width
            else:
                cur.append(tok)
                cur_width += space_width + word_width
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
    # ReportLab's registered TrueType fonts share mutable shaping/subset state.
    with _PDF_LOCK:
        return _build_results_pdf(ans, search_url, entity_names, dedication, lang)


def _build_results_pdf(ans, search_url: str | None, entity_names: list[str] | None,
                       dedication: str, lang: str) -> bytes:
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
    story += _text_flowables(
        _bilingual_text("source_display.pdf_search_parameters", lang),
        11, inner, bold=True,
    )
    for label, value in _search_parameter_rows(search_url, entity_names, lang):
        story += _text_flowables(f"<b>{escape(label)}:</b> {escape(value)}", 9, inner, html=True)
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
        title_text = f"{i + 1}. {primary_title}"
        if is_rtl(lang):
            title_style.alignment = TA_RIGHT
        if re.search(r"[\u0591-\u05c7]", title_text):
            title_style.shaping = 1
            title_markup = _rtl_line_markup([(word, True, False) for word in title_text.split()])
        else:
            title_markup = escape(get_display(title_text, base_dir="R") if is_rtl(lang) else title_text)
        block.append(Paragraph(title_markup, title_style))
        sefaria_url = meta.get_sefaria_url() if hasattr(meta, "get_sefaria_url") else None
        if sefaria_url:
            block.append(_SefariaLink(
                sefaria_url,
                get_text("source_display.open_sefaria", lang),
                lang,
            ))
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
