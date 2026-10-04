# bs"d - lehagdil torah velahadir

import re
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field

from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.EntityObjects.NumberContext import NumberContext
from backend.models_db.Enums import EntityType, NumberCategory


class ENumber(Entity):
    # Ordered tuple of transient field names used for UI display.
    TRANSIENT_DISPLAY_FIELDS: ClassVar[tuple] = (
        "comparedTo",
        "contrastedWith",
    )

    entityType: EntityType = EntityType.ENumber
    numberCategory: Optional[NumberCategory] = None
    en_unit: Optional[str] = None                # Normalized singular noun — what the number counts/measures (e.g., "bull", "year", "silver")
    heb_unit: Optional[str] = None
    # Every context this number (same value + category + unit) was mentioned in
    contexts: List[NumberContext] = Field(default_factory=list)

    def has_metadata(self) -> bool:
        # Numbers never get a display_heb_name (heb_unit/heb_context replace it), so the
        # base display-name check is deliberately not applied here.
        return (
            self.heb_unit is not None
            and bool(self.heb_unit.strip())
            and all(context.heb_context and context.heb_context.strip() for context in self.contexts)
        )

    # ========================= Contexts =========================

    def get_context(self, en_context: str) -> Optional[NumberContext]:
        """The context matching en_context (case-insensitive), or None."""
        return next((context for context in self.contexts if context.matches(en_context)), None)

    def get_contexts_for_source(self, source_key: str) -> List[NumberContext]:
        """The contexts this number was mentioned in within the given source."""
        return [context for context in self.contexts if source_key in context.source_keys]

    def tag_contexts_with_source(self, source_key: str) -> None:
        """Record that every context of this (freshly extracted) number came from source_key."""
        for context in self.contexts:
            if source_key not in context.source_keys:
                context.source_keys.append(source_key)

    def merge_contexts(self, contexts: List[NumberContext]) -> bool:
        """
        Add the given contexts to this number: a context matching an existing one
        (case-insensitive en_context) is merged into it, any other is appended.
        Returns True if anything changed.
        """
        changed = False
        for context in contexts:
            existing = self.get_context(context.en_context)
            if existing is None:
                self.contexts.append(context.model_copy(deep=True))
                changed = True
            elif existing.merge(context):
                changed = True
        return changed

    # ========================= Identity / Equality =========================

    def get_identity_tuple(self) -> tuple:
        """
        Number equality is determined by the combination of value (display_en_name),
        numberCategory and unit — NOT by context: the same number in another context is
        the same entity, with that context added to its contexts list.
        """
        return (
            self.entityType,
            self.display_en_name,
            self.numberCategory,
            self.en_unit.lower() if self.en_unit else None,
        )

    def to_db_dict(self) -> Dict[str, Any]:
        data = super().to_db_dict()
        if isinstance(data.get("numberCategory"), NumberCategory):
            data["numberCategory"] = data["numberCategory"].value
        return data

    def build_existence_query(self) -> Dict[str, Any]:
        """
        Query DB for a Number with the same value (display_en_name), numberCategory and
        unit (case-insensitive) - matching get_identity_tuple.
        """
        from backend.db.DBConstants import DBFields, DBOperators
        query: Dict[str, Any] = {
            DBFields.ENTITY_TYPE: self.entityType.value,
            DBFields.DISPLAY_EN_NAME: self.display_en_name,  # already lowercase
            "numberCategory": self.numberCategory.value if self.numberCategory is not None else None,
        }
        if self.en_unit is not None:
            query["en_unit"] = {DBOperators.REGEX: f"^{re.escape(self.en_unit)}$", DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE}
        else:
            query["en_unit"] = None  # matches documents with no unit
        return query

    # ========================= Factory =========================

    def __str__(self) -> str:
        parts = [self.display_en_name]
        if self.numberCategory:
            parts.append(f"[{self.numberCategory.value}]")
        if self.en_unit:
            parts.append(self.en_unit)
        if self.contexts:
            parts.append(f"({'; '.join(context.en_context for context in self.contexts)})")
        return " ".join(parts)

    @classmethod
    def create_from_entity_data(cls, entity_data: dict, entity_type: EntityType = EntityType.ENumber) -> "ENumber":
        """Create an ENumber from raw JSON entity_data (as produced by the LLM pipeline)."""
        en_name = entity_data.get("en_name", "").strip()

        number_category: Optional[NumberCategory] = None
        category_str = entity_data.get("number_category", "").strip()
        if category_str:
            try:
                number_category = NumberCategory(category_str)
            except ValueError:
                for nc in NumberCategory:
                    if nc.value.lower() == category_str.lower():
                        number_category = nc
                        break

        unit_raw = (entity_data.get("en_unit") or "").strip()
        en_unit = unit_raw.lower() if unit_raw else None

        context_raw = (entity_data.get("en_context") or "").strip()
        heb_unit = (entity_data.get("heb_unit") or "").strip() or None
        heb_context = (entity_data.get("heb_context") or "").strip() or None
        contexts = [NumberContext(en_context=context_raw.lower(), heb_context=heb_context)] if context_raw else []

        return cls(
            display_en_name=en_name,
            all_en_names=[en_name],
            numberCategory=number_category,
            en_unit=en_unit,
            heb_unit=heb_unit,
            contexts=contexts,
        )
