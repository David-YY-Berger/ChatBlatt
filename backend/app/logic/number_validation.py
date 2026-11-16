"""Validation shared by the number-search UI and other clients."""


def number_error(value: str) -> str | None:
    """Return a translation-key suffix for invalid input, or None."""
    s = value.strip()
    if not s:
        return None
    if "/" not in s:
        if "." in s:
            return "error_decimal"
        if "-" in s:
            return "error_negative"
        if not all(c in "0123456789" for c in s):
            return "error_digits"
        if int(s) in (0, 1):
            return "error_small"
    else:
        if "-" in s:
            return "error_negative"
        if "." in s:
            return "error_fraction_decimal"
        if s.count("/") > 1:
            return "error_slashes"
        if not all(c in "0123456789/" for c in s):
            return "error_fraction_digits"
        num, den = s.split("/")
        if not num:
            return "error_numerator_missing"
        if not den:
            return "error_denominator_missing"
        if int(num) == 0:
            return "error_numerator_zero"
        if int(den) == 0:
            return "error_denominator_zero"
        if int(num) == int(den):
            return "error_fraction_one"
    return None
