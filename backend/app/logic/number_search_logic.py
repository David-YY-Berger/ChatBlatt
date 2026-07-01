# bs"d - lehagdil torah velahadir

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.models_db.EntityObjects.ENumber import ENumber
from backend.models_db.Enums import NumberCategory
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata


@dataclass
class NumberResult:
    """One distinct ENumber entity together with its sorted source passages."""
    number: ENumber
    sources: List[SourceMetadata] = field(default_factory=list)

    def __str__(self) -> str:
        sources_str = ", ".join(str(s) for s in self.sources) if self.sources else "no sources"
        return f"NumberResult(number={self.number}, sources=[{sources_str}])"


@dataclass
class NumberSearchResult:
    """
    Structured result of a number search.

    by_category maps:
        NumberCategory (or None) → unit string (or None) → list of NumberResult

    Many ENumber entities share a NumberCategory and even a unit, so the
    two-level map lets the UI group them without redundant headers.
    """
    by_category: Dict[Optional[NumberCategory], Dict[Optional[str], List[NumberResult]]] = field(
        default_factory=dict
    )
    total_count: int = 0  # total distinct ENumber entities found

    def __str__(self) -> str:
        categories = [cat.value if cat else "None" for cat in self.by_category]
        return f"NumberSearchResult(total={self.total_count}, categories=[{', '.join(categories)}])"


class NumberSearchLogic:
    def __init__(self):
        from backend.db.DBFactory import DBFactory
        self.db = DBFactory.get_prod_db_mongo()

    def execute(self, value: str) -> Optional[NumberSearchResult]:
        """
        Find all ENumber entities matching *value* and build a two-level map
        (NumberCategory → unit → [NumberResult]) enriched with source passages.
        Returns None when no matching numbers exist in the DB.
        """
        enumbers: List[ENumber] = self.db.get_enumbers_by_value(value)
        if not enumbers:
            return None

        result = NumberSearchResult(total_count=len(enumbers))

        for number in enumbers:
            cat: Optional[NumberCategory] = number.numberCategory
            unit: Optional[str] = number.unit

            # Ensure nested dicts exist
            if cat not in result.by_category:
                result.by_category[cat] = {}
            if unit not in result.by_category[cat]:
                result.by_category[cat][unit] = []

            sources = self.db.get_source_metadata_by_entity_key(number.key)
            sources_sorted = sorted(sources)  # SourceClass implements __lt__ for canonical order

            result.by_category[cat][unit].append(
                NumberResult(number=number, sources=sources_sorted)
            )

        return result
