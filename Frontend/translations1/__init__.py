# bs"d - lehagdil torah velahadir

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict

import yaml

TRANSLATIONS_DIR = Path(__file__).parent


@functools.lru_cache(maxsize=1)
def _load_translations() -> Dict[str, Dict[str, Any]]:
    translations: Dict[str, Dict[str, Any]] = {}
    for path in TRANSLATIONS_DIR.glob("*.yml"):
        lang_code = path.stem
        with path.open("r", encoding="utf-8") as f:
            translations[lang_code] = yaml.safe_load(f) or {}
    return translations


def available_languages() -> Dict[str, str]:
    # Display names for selection UI.
    return {"en": "English", "he": "עברית"}


def is_rtl(lang: str) -> bool:
    return lang.lower().startswith("he")


def _get_nested(data: Dict[str, Any], path: list[str]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def get_text(key: str, lang: str) -> str:
    translations = _load_translations()
    fallback_lang = "en"
    path = key.split(".")

    value = _get_nested(translations.get(lang, {}), path)
    if value is None and lang != fallback_lang:
        value = _get_nested(translations.get(fallback_lang, {}), path)
    if value is None:
        return key
    return str(value)
