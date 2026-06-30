# bs"d - lehagdil torah velahadir
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NumberSearchRequest:
    number_type: str  # "whole" or "fraction"
    value: str


@dataclass
class NumberSearchResponse:
    success: bool
    error: Optional[str] = None
    data: Optional[dict] = field(default=None)


class NumberSearchController:
    def __init__(self):
        pass

    def handle(self, request: NumberSearchRequest) -> NumberSearchResponse:
        # Logic will be implemented in number_search_logic.py
        return NumberSearchResponse(success=True)
