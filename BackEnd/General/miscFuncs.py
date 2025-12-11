import re

import unicodedata


def clean_en_text_from_html_tags(html_content) -> str:
    # 1. Remove footnote markers and their content (superscript + italic footnotes)
    # This removes things like: <sup class="footnote-marker">a</sup><i class="footnote">...</i>
    text = re.sub(r'<sup class="footnote-marker">[^<]*</sup>\s*<i class="footnote">.*?</i>', ' ', html_content)

    # 2. Handle <small> tags by removing them WITHOUT adding spaces
    # This prevents "G<small>OD</small>" from becoming "G OD"
    text = re.sub(r'<small>', '', text)
    text = re.sub(r'</small>', '', text)

    # 3. Remove all remaining HTML tags (with space replacement)
    text = re.sub(r'<[^>]+>', ' ', text)

    # 4. Normalize unicode (remove accents etc.)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

    # 5. Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def clean_heb_text_from_html_tags(html_content) -> str:
    # 1. Remove span markers like {ס} and {פ} (section markers)
    # These are liturgical/formatting markers: <span class="mam-spi-samekh">{ס}</span>
    text = re.sub(r'<span class="mam-spi-[^"]*">\{[^}]*\}</span>', '', html_content)

    # 2. Remove Keri/Ketiv variants (textual variants in parentheses/brackets)
    # Pattern: <span class="mam-kq"><span class="mam-kq-k">(text)</span> <span class="mam-kq-q">[text]</span></span>
    text = re.sub(r'<span class="mam-kq">.*?</span>', '', text)

    # 3. Handle <small> tags by removing them WITHOUT adding spaces
    # Preserves word integrity for any words split across <small> tags
    text = re.sub(r'<small>', '', text)
    text = re.sub(r'</small>', '', text)

    # 4. Handle <b> tags (often used for cantillation marks like |) without adding spaces
    text = re.sub(r'<b>', '', text)
    text = re.sub(r'</b>', '', text)

    # 5. Remove all remaining HTML tags (with space replacement)
    text = re.sub(r'<[^>]+>', ' ', text)

    # 6. Remove &nbsp; and &thinsp; entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&thinsp;', '')

    # 7. Collapse multiple spaces (but preserve Hebrew text integrity)
    text = re.sub(r' +', ' ', text).strip()

    return text