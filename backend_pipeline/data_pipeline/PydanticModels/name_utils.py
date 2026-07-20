import re


def smart_title_case(s: str) -> str:
    """Title case that does not capitalize after apostrophes (e.g., Putiel's not Putiel'S)."""
    titled = s.strip().title()
    return re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), titled)


__all__ = ["smart_title_case"]

