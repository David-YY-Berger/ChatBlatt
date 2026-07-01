# bs"d - lehagdil torah velahadir
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.app.logic.number_search_logic import NumberSearchLogic, NumberSearchResult


@dataclass
class NumberSearchRequest:
    number_type: str  # "whole" or "fraction"
    value: str

    def __str__(self) -> str:
        return f"NumberSearchRequest(type={self.number_type}, value={self.value!r})"


@dataclass
class NumberSearchResponse:
    success: bool
    error: Optional[str] = None
    result: Optional[NumberSearchResult] = field(default=None)

    def __str__(self) -> str:
        if self.error:
            return f"NumberSearchResponse(success={self.success}, error={self.error!r})"
        return f"NumberSearchResponse(success={self.success}, result={self.result})"


class NumberSearchController:
    def __init__(self):
        self._logic = NumberSearchLogic()

    def handle(self, request: NumberSearchRequest) -> NumberSearchResponse:
        try:
            result = self._logic.execute(request.value)
            return NumberSearchResponse(success=True, result=result)
        except Exception as e:
            return NumberSearchResponse(success=False, error=str(e))
