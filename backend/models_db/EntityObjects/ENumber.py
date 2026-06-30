# bs"d - lehagdil torah velahadir

from typing import Any, Dict, Optional, TYPE_CHECKING
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType, NumberCategory

if TYPE_CHECKING:
    from backend.models_db.EntityObjects.EntityIdentity import EntityIdentityContext


class ENumber(Entity):
    entityType: EntityType = EntityType.ENumber
    numberCategory: Optional[NumberCategory] = None
    unit: Optional[str] = None                # Normalized singular noun — what the number counts/measures (e.g., "bull", "year", "silver")
    context: Optional[str] = None             # 1-6 word topic summary so the number is understandable out of context

    # ========================= Identity / Equality =========================

    def get_identity_tuple(self, context: Optional["EntityIdentityContext"] = None) -> tuple:
        """
        Number equality is determined by the combination of numberCategory, unit, and context —
        not by display_en_name, since many numbers share the same numeric value.
        """
        return (
            self.entityType,
            self.numberCategory,
            self.unit.lower() if self.unit else None,
            self.context.lower() if self.context else None,
        )

    def build_existence_query(self, context: Optional["EntityIdentityContext"] = None) -> Dict[str, Any]:
        """
        Query DB for a Number with the same numberCategory, unit (case-insensitive),
        and context (case-insensitive).
        """
        from backend.db.DBConstants import DBFields, DBOperators
        query: Dict[str, Any] = {DBFields.ENTITY_TYPE: self.entityType.value}
        if self.numberCategory is not None:
            query["numberCategory"] = self.numberCategory.value
        if self.unit is not None:
            query["unit"] = {DBOperators.REGEX: f"^{self.unit}$", DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE}
        if self.context is not None:
            query["context"] = {DBOperators.REGEX: f"^{self.context}$", DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE}
        return query

    # ========================= Factory =========================

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

        unit_raw = entity_data.get("unit", "").strip()
        unit = unit_raw.lower() if unit_raw else None

        context_raw = entity_data.get("context", "").strip()
        context = context_raw.lower() if context_raw else None

        return cls(
            display_en_name=en_name,
            all_en_names=[en_name],
            numberCategory=number_category,
            unit=unit,
            context=context,
        )

