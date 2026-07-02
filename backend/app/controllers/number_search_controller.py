# bs"d - lehagdil torah velahadir
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.app.logic.number_search_logic import NumberSearchLogic, NumberSearchResult
from system_common.Constants import LANG_EN


@dataclass
class NumberSearchRequest:
    number_type: str  # "whole" or "fraction"
    value: str
    lang: str = LANG_EN  # UI language — "en" or "he"

    def __str__(self) -> str:
        return f"NumberSearchRequest(type={self.number_type}, value={self.value!r}, lang={self.lang!r})"


@dataclass
class NumberSearchResponse:
    success: bool
    error: Optional[str] = None
    result: Optional[NumberSearchResult] = field(default=None)

    def __str__(self) -> str:
        if self.error:
            return f"NumberSearchResponse(success={self.success}, error={self.error!r})"
        return f"NumberSearchResponse(success={self.success}, result={self.result})"


def _parse_number_value(value: str) -> str:
    """
    Normalise a user-supplied number string to a plain decimal string.

    Handles:
      - whole numbers  e.g. "7"   → "7"
      - fractions      e.g. "1/2" → "0.5"

    The result is formatted without a trailing zero when the division is exact
    (e.g. "1/2" → "0.5", not "0.50"), but keeps enough precision otherwise.
    """
    s = value.strip()
    if "/" in s:
        numerator, denominator = s.split("/", 1)
        result = int(numerator) / int(denominator)
        # Remove unnecessary trailing zeros while keeping it a plain string
        formatted = f"{result:g}"
        return formatted
    return s


class NumberSearchController:
    def __init__(self):
        self._logic = NumberSearchLogic()

    def handle(self, request: NumberSearchRequest) -> NumberSearchResponse:
        try:
            normalised_value = _parse_number_value(request.value)
            result = self._logic.execute(normalised_value, request.lang)
            return NumberSearchResponse(success=True, result=result)
        except Exception as e:
            return NumberSearchResponse(success=False, error=str(e))
