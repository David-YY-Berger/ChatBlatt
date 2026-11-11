# bs"d - lehagdil torah velahadir

from collections import Counter

from translations1 import enum_text, is_rtl


def format_entity_option_label(opt, lang: str = "en") -> str:
    if is_rtl(lang) and opt.display_heb_name:
        label = f"{opt.display_heb_name} ({opt.display_en_name})"
    elif opt.display_heb_name:
        label = f"{opt.display_en_name} ({opt.display_heb_name})"
    else:
        label = opt.display_en_name

    roles = ", ".join(enum_text(role, lang) for role in getattr(opt, "roles", []))
    if roles:
        label += f" - {roles}"
    period = getattr(opt, "timePeriod", None)
    if period is not None:
        label += f" [{enum_text(period, lang)}]"
    return label


def unique_entity_option_labels(options: list, lang: str = "en") -> list[str]:
    """Keep disambiguation consistent across languages and selector surfaces."""
    canonical = [format_entity_option_label(opt) for opt in options]
    counts = Counter(canonical)
    suffix_counts = Counter(
        (label, opt.key[-4:]) for label, opt in zip(canonical, options)
    )
    labels = [format_entity_option_label(opt, lang) for opt in options]
    return [
        f"{label} (#{opt.key[-4:] if suffix_counts[(base, opt.key[-4:])] == 1 else opt.key})"
        if counts[base] > 1 else label
        for label, base, opt in zip(labels, canonical, options)
    ]
