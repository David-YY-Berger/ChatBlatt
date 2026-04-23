import logging
from typing import List, Optional, Set

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.models.Enums import NumberCategory
from backend.models.PydanticModels.name_utils import smart_title_case
from backend.models.PydanticModels.number_normalization import _normalize_number_string
from backend.models.PydanticModels.pydantic_constants import (
    DEMONYM_TO_NATION,
    ENTITY_CATEGORIES,
    TRIBES_OF_ISRAEL,
    _NUMBER_CATEGORY_VALUES,
)

logger = logging.getLogger(__name__)


class Entity(BaseModel):
    en_name: str = Field(min_length=1, description="Entity name cannot be empty")

    @field_validator("en_name")
    @classmethod
    def normalize_to_proper_noun(cls, v: str) -> str:
        """Normalize entity name to proper noun format (title case)."""
        return smart_title_case(v)


class NumberEntity(BaseModel):
    """Pydantic model for Number entities extracted by the LLM.
    Extends the basic entity with category, unit, and context."""

    en_name: str = Field(min_length=1, description="The numeric value as a string (e.g., '7', '40', '3.5')")
    number_category: str = Field(
        description=(
            "The category this number describes. "
            f"Must be one of: {', '.join(_NUMBER_CATEGORY_VALUES)}"
        )
    )
    unit: str = Field(
        description=(
            "A normalized, singular noun describing what is being counted or measured. "
            "Examples: 'bull', 'year', 'silver', 'cubit', 'tribe', 'lash'. "
            "Must be a single, lowercase, singular English word - no plurals, no phrases."
        )
    )
    context: str = Field(
        description=(
            "A 1-6 word topic summary so this number is understandable outside the original passage. "
            "Describe the general subject being discussed - someone seeing this entry elsewhere "
            "should immediately understand what this number is about. "
            "Examples: 'tabernacle construction', 'korbanot on sukkot', 'census in wilderness', "
            "'noahs lifespan', 'punishment for theft'."
        )
    )

    @field_validator("number_category")
    @classmethod
    def validate_number_category(cls, v: str) -> str:
        """Ensure number_category is a valid NumberCategory. Falls back to Misc if unknown."""
        valid = {e.description for e in NumberCategory}
        if v not in valid:
            match = next((cat for cat in valid if cat.lower() == v.lower()), None)
            if match:
                return match
            logger.warning(
                f"Unknown number_category '{v}' - falling back to 'Misc'. "
                f"Valid categories: {', '.join(sorted(valid))}"
            )
            return NumberCategory.Misc.description
        return v

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, v: str) -> str:
        """Normalize unit to lowercase singular noun."""
        v = v.strip().lower()
        if v.endswith("es") and len(v) > 3 and v not in ("incense", "frankincense", "bronze"):
            v = v[:-2] if v.endswith("ies") else v[:-1] if v.endswith("ses") or v.endswith("zes") else v[:-2]
        elif v.endswith("s") and not v.endswith("ss") and len(v) > 2:
            v = v[:-1]
        if not v:
            raise ValueError("unit cannot be empty")
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: str) -> str:
        """Ensure context is 1-6 words and normalized."""
        v = v.strip().lower()
        word_count = len(v.split())
        if word_count < 1:
            raise ValueError("context cannot be empty")
        if word_count > 6:
            raise ValueError(f"context must be 1-6 words, got {word_count}: '{v}'")
        return v


class Entities(BaseModel):
    Person: Optional[List[Entity]] = Field(
        default_factory=list,
        description="Individuals AND groups of people (e.g., Moses, The 70 Elders, Children of Israel)",
    )
    Place: Optional[List[Entity]] = Field(default_factory=list)
    TribeOfIsrael: Optional[List[Entity]] = Field(default_factory=list)
    Nation: Optional[List[Entity]] = Field(default_factory=list)
    Symbol: Optional[List[Entity]] = Field(default_factory=list)
    Number: Optional[List[NumberEntity]] = Field(
        default_factory=list,
        description=(
            "Explicit numeric values with context. Each number must include: "
            "en_name (the numeric value), number_category (one of: "
            f"{', '.join(_NUMBER_CATEGORY_VALUES)}), "
            "unit (normalized singular noun - what is counted/measured), and context (1-6 word topic summary)."
        ),
    )
    Animal: Optional[List[Entity]] = Field(
        default_factory=list,
        description="Real and mythical animals (e.g., Lion, Eagle, Serpent, Balaam's Donkey)",
    )
    Food: Optional[List[Entity]] = Field(
        default_factory=list,
        description="Food items in normalized singular form (e.g., Bread, Manna, Wine)",
    )
    Plant: Optional[List[Entity]] = Field(
        default_factory=list,
        description="Plants (edible and inedible) in normalized singular form (e.g., Grape, Fig, Cedar)",
    )

    @field_validator("Number")
    @classmethod
    def validate_numbers(cls, v: Optional[List[NumberEntity]]) -> Optional[List[NumberEntity]]:
        """Validate and normalize Number entities to canonical numeric strings."""
        if not v:
            return v

        valid_numbers = []
        for entity in v:
            normalized = _normalize_number_string(entity.en_name)
            if normalized is None:
                logger.warning(f"Filtered invalid Number entity: '{entity.en_name}'")
                continue
            valid_numbers.append(
                NumberEntity(
                    en_name=normalized,
                    number_category=entity.number_category,
                    unit=entity.unit,
                    context=entity.context,
                )
            )

        return valid_numbers if valid_numbers else None

    @field_validator("TribeOfIsrael")
    @classmethod
    def validate_tribes(cls, v: Optional[List[Entity]]) -> Optional[List[Entity]]:
        """Validate that TribeOfIsrael entities are actual tribes."""
        if not v:
            return v

        valid_tribes = []
        for entity in v:
            if entity.en_name.lower() in TRIBES_OF_ISRAEL:
                valid_tribes.append(entity)
            else:
                logger.warning(f"Filtered invalid tribe: '{entity.en_name}' (not in known tribes list)")

        return valid_tribes if valid_tribes else None

    @field_validator("Nation")
    @classmethod
    def convert_demonyms_to_nations(cls, v: Optional[List[Entity]]) -> Optional[List[Entity]]:
        """Convert demonyms (e.g., Aramean) to proper nation names (e.g., Aram)."""
        if not v:
            return v

        corrected = []
        for entity in v:
            name_lower = entity.en_name.lower()
            if name_lower in DEMONYM_TO_NATION:
                corrected_name = DEMONYM_TO_NATION[name_lower]
                logger.info(f"Auto-corrected demonym: '{entity.en_name}' -> '{corrected_name}'")
                corrected.append(Entity(en_name=corrected_name))
            else:
                corrected.append(entity)

        return corrected if corrected else None

    @field_validator("Person", "Nation")
    @classmethod
    def validate_proper_nouns(cls, v: Optional[List[Entity]], info) -> Optional[List[Entity]]:
        """Filter out generic common nouns from Person and Nation."""
        if not v:
            return v

        GENERIC_PERSON_WORDS = {
            "king",
            "priest",
            "prophet",
            "leader",
            "man",
            "woman",
            "child",
            "servant",
            "warrior",
            "elder",
            "judge",
            "scribe",
            "soldier",
            "messenger",
            "person",
            "people",
            "men",
            "women",
            "children",
            "elders",
            "my people",
            "his people",
            "your people",
            "their people",
            "my servants",
            "his servants",
            "he who",
            "she who",
            "they who",
            "those who",
            "one who",
            "whoever",
            "anyone",
            "someone",
        }

        GENERIC_NATION_WORDS = {
            "nation",
            "nations",
            "people",
            "peoples",
            "enemy",
            "enemies",
            "army",
            "armies",
            "kingdom",
            "kingdoms",
            "tribe",
            "tribes",
        }

        generic_words = GENERIC_PERSON_WORDS if info.field_name == "Person" else GENERIC_NATION_WORDS

        valid_entities = []
        filtered_count = 0

        for entity in v:
            if entity.en_name.lower() in generic_words:
                filtered_count += 1
                logger.warning(
                    f"Filtered generic word from {info.field_name}: '{entity.en_name}' "
                    f"(not a proper noun)"
                )
            else:
                valid_entities.append(entity)

        if filtered_count > 0:
            logger.info(f"Filtered {filtered_count} generic words from {info.field_name}")

        return valid_entities if valid_entities else None

    @model_validator(mode="after")
    def exclude_from_symbol_if_in_other_categories(self):
        """
        If an entity appears in Animal, Food, or Plant, it should NOT appear in Symbol.
        Remove such entities from Symbol.
        """
        if not self.Symbol:
            return self

        excluded_names = set()
        for category in ["Animal", "Food", "Plant"]:
            entity_list = getattr(self, category, None)
            if entity_list:
                excluded_names.update(e.en_name.lower() for e in entity_list)

        if not excluded_names:
            return self

        original_count = len(self.Symbol)
        self.Symbol = [entity for entity in self.Symbol if entity.en_name.lower() not in excluded_names]

        removed_count = original_count - len(self.Symbol)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} entities from Symbol (already in Animal/Food/Plant)")

        if not self.Symbol:
            self.Symbol = None

        return self

    @model_validator(mode="after")
    def ensure_entity_overlap(self):
        """
        Auto-correct entity classification based on priority rules:
        - TribeOfIsrael entities should also appear in Person (tribes are named after people)
        - This ensures relationships like childOfFather, childOfMother, bornIn work for tribe patriarchs
        """
        if self.TribeOfIsrael:
            if not self.Person:
                self.Person = []

            existing_persons = {e.en_name.lower() for e in self.Person}

            for tribe_entity in self.TribeOfIsrael:
                if tribe_entity.en_name.lower() not in existing_persons:
                    self.Person.append(Entity(en_name=tribe_entity.en_name))
                    existing_persons.add(tribe_entity.en_name.lower())
                    logger.warning(
                        f"Auto-added '{tribe_entity.en_name}' to Person "
                        f"(was only in TribeOfIsrael)"
                    )

        return self

    @model_validator(mode="after")
    def deduplicate_entities(self):
        """Remove duplicate entities within each category."""
        for category in ENTITY_CATEGORIES:
            entity_list = getattr(self, category, None)
            if not entity_list:
                continue

            seen = set()
            unique = []
            for entity in entity_list:
                name_lower = entity.en_name.lower()
                if name_lower not in seen:
                    unique.append(entity)
                    seen.add(name_lower)
                else:
                    logger.debug(f"Deduplicated entity in {category}: '{entity.en_name}'")

            setattr(self, category, unique if unique else None)

        return self

    def get_all_entity_names(self) -> Set[str]:
        """Helper to get all entity names across all categories."""
        names = set()
        for category in ENTITY_CATEGORIES:
            entity_list = getattr(self, category, None)
            if entity_list:
                names.update(e.en_name for e in entity_list)
        return names

    def get_all_entity_names_lower(self) -> dict:
        """Helper to get mapping of lowercase entity names to actual names."""
        name_map = {}
        for category in ENTITY_CATEGORIES:
            entity_list = getattr(self, category, None)
            if entity_list:
                for e in entity_list:
                    name_map[e.en_name.lower()] = e.en_name
        return name_map

    def find_matching_entity(self, term: str) -> Optional[str]:
        """
        Find a matching entity name for a relationship term.
        Handles case differences and simple plural forms (e.g., 'Chickens' -> 'Chicken').
        Returns the actual entity name if found, None otherwise.
        """
        all_entities = self.get_all_entity_names()

        if term in all_entities:
            return term

        name_map = self.get_all_entity_names_lower()
        term_lower = term.lower()
        if term_lower in name_map:
            return name_map[term_lower]

        for suffix in ("s", "es", "ies"):
            if term_lower.endswith(suffix):
                singular = term_lower[: -len(suffix)]
                if suffix == "ies":
                    singular += "y"
                if singular in name_map:
                    return name_map[singular]

        return None

    def get_entities_by_type(self, entity_type: str) -> Set[str]:
        """Get entity names for a specific type."""
        entity_list = getattr(self, entity_type, None)
        return {e.en_name for e in entity_list} if entity_list else set()


__all__ = ["Entity", "NumberEntity", "Entities"]

