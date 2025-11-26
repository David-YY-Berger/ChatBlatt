import re

import unicodedata


def clean_text_from_html_tags(html_content) -> str:
    # 1. Remove all HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)

    # 2. Normalize unicode (remove accents etc.)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

    # 3. Lowercase
    text = text.lower()

    # 4. Remove unwanted characters (keep letters, numbers, and useful punctuation)
    text = re.sub(r"[^a-z0-9\s\.,!?;:'\"()\-\[\]{}]", " ", text)

    # 5. Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text