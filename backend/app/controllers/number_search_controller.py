# bs"d - lehagdil torah velahadir
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.app.logic.number_search_logic import NumberSearchLogic, NumberSearchResult, UnitSearchResult
from system_common.Constants import LANG_EN


@dataclass
class UnitSearchRequest:
    unit: str
    lang: str = LANG_EN


@dataclass
class UnitSearchResponse:
    success: bool
    error: Optional[str] = None
    result: Optional[UnitSearchResult] = field(default=None)


@dataclass
class NumberSearchRequest:
    value: str  # whole number (e.g. "7") or fraction (e.g. "1/3"); type is auto-detected
    lang: str = LANG_EN  # UI language — "en" or "he"

    def __str__(self) -> str:
        return f"NumberSearchRequest(value={self.value!r}, lang={self.lang!r})"


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

    def list_units(self) -> list:
        try:
            return self._logic.list_units()
        except Exception:
            return []

    def handle_unit(self, request: UnitSearchRequest) -> UnitSearchResponse:
        try:
            if not request.unit.strip():
                return UnitSearchResponse(success=False, error="Unit is empty")
            return UnitSearchResponse(success=True, result=self._logic.execute_by_unit(request.unit, request.lang))
        except Exception as e:
            return UnitSearchResponse(success=False, error=str(e))
