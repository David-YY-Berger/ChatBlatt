# bs"d - lehagdil torah velahadir

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.models_db.EntityObjects.ENumber import ENumber
from backend.models_db.Enums import NumberCategory


@dataclass
class NumberOccurrenceDTO:
    """
    One (ENumber × SourceMetadata) occurrence enriched with display strings.
    All five fields come directly from the ENumber entity and its SourceMetadata.
    """
    unit: Optional[str]       # number.unit
    context: Optional[str]    # number.context
    source_str: str           # SourceClass.__str__() or to_heb_str() depending on lang
    summary: Optional[str]    # SourceMetadata.summary_en or summary_heb depending on lang
    source_key: str           # SourceMetadata.key

    def __str__(self) -> str:
        return (
            f"NumberOccurrenceDTO(unit={self.unit!r}, context={self.context!r}, "
            f"source={self.source_str!r}, source_key={self.source_key!r})"
        )


@dataclass
class NumberSearchResult:
    """
    Structured result of a number search.

    by_category maps:
        NumberCategory (or None) → list of NumberOccurrenceDTO

    Many ENumber entities share a NumberCategory and even a unit; unit is stored
    inside each DTO so the UI can sub-group without a nested dict.
    """
    by_category: Dict[Optional[NumberCategory], List[NumberOccurrenceDTO]] = field(
        default_factory=dict
    )
    total_count: int = 0  # total (ENumber × source) occurrence pairs found

    def __str__(self) -> str:
        categories = [cat.value if cat else "None" for cat in self.by_category]
        return f"NumberSearchResult(total={self.total_count}, categories=[{', '.join(categories)}])"


class NumberSearchLogic:
    def __init__(self):
        from backend.db.DBFactory import DBFactory
        self.db = DBFactory.get_prod_db_mongo()

    def execute(self, value: str, lang: str = "en") -> Optional[NumberSearchResult]:
        """
        Find all ENumber entities matching *value* and build a map of
        NumberCategory → [NumberOccurrenceDTO], where each DTO holds the five
        relevant display fields for one (ENumber × SourceMetadata) occurrence.

        Sources are sorted canonically (TN < MS < BT < ...) via SourceClass.__lt__.
        Returns None when no matching numbers exist in the DB.
        """
        enumbers: List[ENumber] = self.db.get_enumbers_by_value(value)
        if not enumbers:
            print("no numbers found in db call")
            return None

        by_category: Dict[Optional[NumberCategory], List[NumberOccurrenceDTO]] = {}
        total_count = 0

        for number in enumbers:
            cat: Optional[NumberCategory] = number.numberCategory

            sources = self.db.get_source_metadata_by_entity_key(number.key)
            sources_sorted = sorted(sources)  # SourceClass implements __lt__ for canonical order

            if cat not in by_category:
                by_category[cat] = []

            for src in sources_sorted:
                source_str = src.to_heb_str() if lang == "he" else str(src)
                summary = src.summary_heb if lang == "he" else src.summary_en

                by_category[cat].append(
                    NumberOccurrenceDTO(
                        unit=number.unit,
                        context=number.context,
                        source_str=source_str,
                        summary=summary,
                        source_key=src.key,
                    )
                )
                total_count += 1

        if total_count == 0:
            return None

        return NumberSearchResult(by_category=by_category, total_count=total_count)
