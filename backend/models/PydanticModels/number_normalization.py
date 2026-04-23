import re
from typing import Optional

# Word-to-number mappings for parsing textual numbers
_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_NUMBER_SCALES = {"hundred": 100, "thousand": 1000, "million": 1000000}
_FRACTION_WORDS = {
    "half": 2,
    "third": 3,
    "quarter": 4,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
# Special misspellings to correct (per user requirement: 'thiry seven' -> '40')
_SPECIAL_CORRECTIONS = {
    "thiry seven": "40",
    "thiry": "thirty",
    "fourty": "forty",
}


def _normalize_number_string(raw: str) -> Optional[str]:
    """
    Normalize a number input to a canonical numeric string.
    Handles: integers, decimals, fractions (3/4), word numbers (thirty seven).
    Returns None if the input cannot be parsed as a number.
    """
    text = raw.strip()
    if not text:
        return None

    lowered = text.lower()
    if lowered in _SPECIAL_CORRECTIONS:
        result = _SPECIAL_CORRECTIONS[lowered]
        if re.fullmatch(r"-?\d+\.?\d*", result):
            return result
        text = result

    cleaned = text.replace(",", "").replace("_", "")
    try:
        num = float(cleaned)
        return str(int(num)) if num == int(num) else str(num)
    except ValueError:
        pass

    frac_match = re.fullmatch(r"(-?\d+)\s*/\s*(\d+)", cleaned)
    if frac_match:
        num, denom = int(frac_match.group(1)), int(frac_match.group(2))
        if denom != 0:
            result = num / denom
            return str(int(result)) if result == int(result) else str(round(result, 6)).rstrip("0").rstrip(".")
        return None

    mixed_match = re.fullmatch(r"(-?\d+)\s+(\d+)\s*/\s*(\d+)", cleaned)
    if mixed_match:
        whole, num, denom = int(mixed_match.group(1)), int(mixed_match.group(2)), int(mixed_match.group(3))
        if denom != 0:
            result = whole + (num / denom)
            return str(int(result)) if result == int(result) else str(round(result, 6)).rstrip("0").rstrip(".")
        return None

    return _parse_word_number(text.lower())


def _parse_word_number(text: str) -> Optional[str]:
    """Parse word numbers like 'thirty seven', 'two hundred', 'one half'."""
    for wrong, right in _SPECIAL_CORRECTIONS.items():
        text = text.replace(wrong, right)

    words = re.split(r"[\s-]+", text.strip())
    words = [w for w in words if w and w != "and"]

    if not words:
        return None

    if words[-1] in _FRACTION_WORDS or (words[-1].endswith("s") and words[-1][:-1] in _FRACTION_WORDS):
        frac_word = words[-1][:-1] if words[-1].endswith("s") else words[-1]
        denom = _FRACTION_WORDS.get(frac_word)
        if denom:
            numerator_words = words[:-1]
            if not numerator_words:
                numerator = 1
            else:
                num_str = _parse_word_number(" ".join(numerator_words))
                numerator = int(num_str) if num_str and num_str.isdigit() else None
            if numerator is not None:
                result = numerator / denom
                return str(int(result)) if result == int(result) else str(round(result, 6)).rstrip("0").rstrip(".")

    total = 0
    current = 0

    for word in words:
        if word in _NUMBER_WORDS:
            current += _NUMBER_WORDS[word]
        elif word == "hundred":
            current = (current if current else 1) * 100
        elif word == "thousand":
            current = (current if current else 1) * 1000
            total += current
            current = 0
        elif word == "million":
            current = (current if current else 1) * 1000000
            total += current
            current = 0
        else:
            return None

    total += current
    return str(total) if total > 0 or (len(words) == 1 and words[0] == "zero") else None


__all__ = [
    "_NUMBER_WORDS",
    "_NUMBER_SCALES",
    "_FRACTION_WORDS",
    "_SPECIAL_CORRECTIONS",
    "_normalize_number_string",
    "_parse_word_number",
]


