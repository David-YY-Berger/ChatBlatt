# bs"d - lehagdil torah velahadir

import re

import unicodedata


def clean_en_text_from_html_tags(html_content) -> str:

    # 0. Replace the tetragrammaton before processing
    text = html_content.replace('יהוה', 'HASHEM')

    # 1. Remove footnote markers and their content (superscript + italic footnotes)
    # This removes things like: <sup class="footnote-marker">a</sup><i class="footnote">...</i>
    text = re.sub(r'<sup class="footnote-marker">[^<]*</sup>\s*<i class="footnote">.*?</i>', '', text)  # Changed ' ' to ''

    # 2. Handle <small> tags by removing them WITHOUT adding spaces
    # This prevents "G<small>OD</small>" from becoming "G OD"
    text = re.sub(r'<small>', '', text)
    text = re.sub(r'</small>', '', text)

    # 3. Remove all remaining HTML tags (with space replacement)
    text = re.sub(r'<[^>]+>', ' ', text)

    # 4. Normalize unicode but preserve common punctuation
    # First, replace smart quotes and dashes with ASCII equivalents
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('—', '-').replace('–', '-')
    # Then normalize remaining unicode
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

    # 7. Replace maqaf (U+05BE), the Hebrew "hyphen" used to join words
    # (e.g. בְּנֵֽי־יִשְׂרָאֵ֛ל), with a space so words don't get glued together
    # once the diacritics are stripped below.
    text = text.replace('\u05be', ' ')

    # 8. Keep sof pasuq (U+05C3), the Hebrew "sentence end" marker, by
    # converting it to a regular colon so sentence boundaries survive cleanup.
    text = text.replace('\u05c3', ':')

    # 9. Strip Hebrew vowels (niqqud), cantillation marks (te'amim), and other
    # combining diacritics, leaving just the plain Hebrew letters.
    # This covers the full Hebrew diacritics block (U+0591-U+05C7), excluding
    # sof pasuq (U+05C3) which was already converted to ':' above.
    text = re.sub(r'[\u0591-\u05C2\u05C4-\u05C7]', '', text)

    # 10. Collapse multiple spaces (but preserve Hebrew text integrity)
    text = re.sub(r' +', ' ', text).strip()

    return text