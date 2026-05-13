# bs"d - lehagdil torah velahadir
"""
Section sorting logic for different source types.

BT (Babylonian Talmud) sections use folio notation: e.g. "14b:5-8", "14a:11-14b:3", "19a:11"
TN (Tanach) sections use chapter:verse notation: e.g. "5:13–6:27", "1:1–24", "18:1–18:10"

Each SourceType gets its own sort-key strategy via a registry pattern.
"""
import re
from typing import Callable, Tuple


def _normalize_separator(section: str) -> str:
    """Replace en-dash, em-dash with hyphen for uniform parsing."""
    return section.replace("\u2013", "-").replace("\u2014", "-")


# ─────────────────────────── BT (Talmud) Sorting ───────────────────────────

def _parse_bt_folio(token: str) -> Tuple[int, int, int]:
    """
    Parse a BT folio reference like '14b:5' into a sortable tuple (page, side, line).
    - page: integer page number
    - side: 0 for 'a', 1 for 'b'
    - line: line number (0 if absent)
    """
    match = re.match(r"(\d+)([ab])(?::(\d+))?", token.strip())
    if match:
        page = int(match.group(1))
        side = 0 if match.group(2) == "a" else 1
        line = int(match.group(3)) if match.group(3) else 0
        return (page, side, line)
    # Fallback: try pure number (shouldn't happen for BT, but be safe)
    return (0, 0, 0)


def bt_section_sort_key(section: str) -> Tuple:
    """
    Return a sortable key for a BT section string.
    Examples: '14b:5-8', '14a:11-14b:3', '19a:11'
    We sort by the START of the range.
    """
    section = _normalize_separator(section)
    # Take only the start part (before the range separator)
    start = section.split("-")[0].strip()
    return _parse_bt_folio(start)


# ─────────────────────────── TN (Tanach) Sorting ───────────────────────────

def _parse_tn_ref(token: str) -> Tuple[int, int]:
    """
    Parse a TN reference like '5:13' into (chapter, verse).
    If only a number like '24', treat as (0, number) — i.e. verse-only within same chapter.
    """
    token = token.strip()
    if ":" in token:
        parts = token.split(":")
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            return (0, 0)
    else:
        # Just a verse number (continuation within same chapter)
        try:
            return (0, int(token))
        except ValueError:
            return (0, 0)


def tn_section_sort_key(section: str) -> Tuple:
    """
    Return a sortable key for a TN section string.
    Examples: '5:13–6:27', '1:1–24', '18:1–18:10'
    We sort by the START of the range.
    """
    section = _normalize_separator(section)
    start = section.split("-")[0].strip()
    return _parse_tn_ref(start)


# ─────────────────────────── Generic / Fallback ───────────────────────────

def generic_section_sort_key(section: str) -> Tuple:
    """Fallback: extract all leading digits for a rough numeric sort."""
    section = _normalize_separator(section)
    nums = re.findall(r"\d+", section)
    return tuple(int(n) for n in nums) if nums else (0,)


# ─────────────────────────── Registry ───────────────────────────

# Maps SourceType name -> sort key function
_SORT_KEY_REGISTRY: dict[str, Callable] = {
    "BT": bt_section_sort_key,
    "JT": bt_section_sort_key,   # Jerusalem Talmud uses similar folio logic
    "TN": tn_section_sort_key,
    "MS": tn_section_sort_key,   # Mishna uses chapter:mishna notation
    "RM": tn_section_sort_key,   # Rambam uses chapter:halacha notation
}


def get_section_sort_key(source_type_name: str, section: str) -> Tuple:
    """
    Get the sort key for a section, dispatching to the correct strategy
    based on the source type name (e.g. 'BT', 'TN').
    """
    fn = _SORT_KEY_REGISTRY.get(source_type_name, generic_section_sort_key)
    return fn(section)


def source_entry_sort_key(entry: Tuple[str, dict]) -> Tuple:
    """
    Sort key for a (source_key, data) entry, ordering by book then by section.
    Suitable for use as a key= argument when sorting JSON entry lists.
    """
    # Import here to avoid circular imports at module load time
    from backend.models_db.SourceClasses.SourceClass import SourceClass

    src_key = entry[0]
    book = SourceClass.get_book_from_key(src_key)
    book_order = book.order if book else 0
    src_type_name = src_key[:2] if src_key else ""
    section = SourceClass.get_section_from_key(src_key) if src_key else ""
    return (book_order, get_section_sort_key(src_type_name, section))



