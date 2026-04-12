# bs"d - lehagdil torah velahadir

from typing import List, Optional, Literal, Set
from pydantic import BaseModel, Field, field_validator, model_validator
import logging
import re

from BackEnd.DataObjects.Enums import NumberCategory

logger = logging.getLogger(__name__)

# --- Global Constants ---
TRIBES_OF_ISRAEL = {
    'reuben', 'simeon', 'levi', 'judah', 'dan', 'naphtali',
    'gad', 'asher', 'issachar', 'zebulun', 'joseph', 'benjamin',
    'ephraim', 'manasseh'
}

# Entity category names - used for validation and iteration
ENTITY_CATEGORIES = ('Person', 'Place', 'TribeOfIsrael', 'Nation', 'Symbol', 'Number', 'Animal', 'Food', 'Plant')

# Demonym to Nation name mapping (lowercase keys for matching)
# Includes nations from Tanach, Talmud, and Midrash
DEMONYM_TO_NATION = {
    # === Major Biblical Nations ===
    'aramean': 'Aram',
    'arameans': 'Aram',
    'syrian': 'Syria',  # Aram often called Syria
    'syrians': 'Syria',
    'egyptian': 'Egypt',
    'egyptians': 'Egypt',
    'moabite': 'Moab',
    'moabites': 'Moab',
    'ammonite': 'Ammon',
    'ammonites': 'Ammon',
    'edomite': 'Edom',
    'edomites': 'Edom',
    'philistine': 'Philistia',
    'philistines': 'Philistia',
    'assyrian': 'Assyria',
    'assyrians': 'Assyria',
    'babylonian': 'Babylon',
    'babylonians': 'Babylon',
    'chaldean': 'Chaldea',  # Chaldeans ruled Babylon
    'chaldeans': 'Chaldea',
    'persian': 'Persia',
    'persians': 'Persia',
    'median': 'Media',
    'medians': 'Media',
    'mede': 'Media',
    'medes': 'Media',
    'greek': 'Greece',
    'greeks': 'Greece',

    # === Canaanite Nations (Seven Nations) ===
    'canaanite': 'Canaan',
    'canaanites': 'Canaan',
    'hittite': 'Hittites',
    'hittites': 'Hittites',
    'amalekite': 'Amalek',
    'amalekites': 'Amalek',
    'midianite': 'Midian',
    'midianites': 'Midian',
    'ishmaelite': 'Ishmael',
    'ishmaelites': 'Ishmael',
    'kenite': 'Kenites',
    'kenites': 'Kenites',
    'jebusite': 'Jebusites',
    'jebusites': 'Jebusites',
    'girgashite': 'Girgashites',
    'girgashites': 'Girgashites',
    'hivite': 'Hivites',
    'hivites': 'Hivites',
    'perizzite': 'Perizzites',
    'perizzites': 'Perizzites',
}

# Symmetric relationships where (A, B) == (B, A)
SYMMETRIC_RELATIONSHIPS = ('spouseOf', 'spokeWith', 'disagreedWith', 'EnemyOf', 'AllyOf', 'AliasOf', 'comparedTo', 'contrastedWith')

# Person → Place relationships that supersede associatedWithPlace
# If a (person, place) pair exists in any of these, it should NOT appear in associatedWithPlace
PERSON_PLACE_SPECIFIC_RELATIONSHIPS = ('bornIn', 'diedIn', 'visited', 'prayedAt')

max_len_summary: int = 10
min_len_summary: int = 4


def smart_title_case(s: str) -> str:
    """Title case that doesn't capitalize after apostrophes (e.g., Putiel's not Putiel'S)."""
    # First apply standard title case
    titled = s.strip().title()
    # Then fix apostrophe cases: replace X'Y with X'y (lowercase after apostrophe)
    return re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), titled)


# --- Number Normalization ---
# Word-to-number mappings for parsing textual numbers
_NUMBER_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
    'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
}
_NUMBER_SCALES = {'hundred': 100, 'thousand': 1000, 'million': 1000000}
_FRACTION_WORDS = {
    'half': 2, 'third': 3, 'quarter': 4, 'fourth': 4, 'fifth': 5,
    'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
}
# Special misspellings to correct (per user requirement: 'thiry seven' -> '40')
_SPECIAL_CORRECTIONS = {
    'thiry seven': '40',
    'thiry': 'thirty',
    'fourty': 'forty',
}


def _normalize_number_string(raw: str) -> Optional[str]:
    """
    Normalize a number input to a canonical numeric string.
    Handles: integers, decimals, fractions (3/4), word numbers (thirty seven).
    Returns None if the input cannot be parsed as a number.
    """
    text = raw.strip()
    if not text:
        return None

    # Check for special corrections first
    lowered = text.lower()
    if lowered in _SPECIAL_CORRECTIONS:
        result = _SPECIAL_CORRECTIONS[lowered]
        # If correction is a number string, return it directly
        if re.fullmatch(r'-?\d+\.?\d*', result):
            return result
        # Otherwise it's a word correction, continue processing
        text = result

    # Try direct numeric parsing (integers, decimals)
    cleaned = text.replace(',', '').replace('_', '')
    try:
        num = float(cleaned)
        # Return as int string if whole number, else decimal
        return str(int(num)) if num == int(num) else str(num)
    except ValueError:
        pass

    # Try fraction format: "3/4" or "1 3/4"
    frac_match = re.fullmatch(r'(-?\d+)\s*/\s*(\d+)', cleaned)
    if frac_match:
        num, denom = int(frac_match.group(1)), int(frac_match.group(2))
        if denom != 0:
            result = num / denom
            return str(int(result)) if result == int(result) else str(round(result, 6)).rstrip('0').rstrip('.')
        return None

    # Try mixed fraction: "2 1/2"
    mixed_match = re.fullmatch(r'(-?\d+)\s+(\d+)\s*/\s*(\d+)', cleaned)
    if mixed_match:
        whole, num, denom = int(mixed_match.group(1)), int(mixed_match.group(2)), int(mixed_match.group(3))
        if denom != 0:
            result = whole + (num / denom)
            return str(int(result)) if result == int(result) else str(round(result, 6)).rstrip('0').rstrip('.')
        return None

    # Try word number parsing
    return _parse_word_number(text.lower())


def _parse_word_number(text: str) -> Optional[str]:
    """Parse word numbers like 'thirty seven', 'two hundred', 'one half'."""
    # Apply corrections for misspellings
    for wrong, right in _SPECIAL_CORRECTIONS.items():
        text = text.replace(wrong, right)

    words = re.split(r'[\s-]+', text.strip())
    words = [w for w in words if w and w != 'and']

    if not words:
        return None

    # Check for fraction words (e.g., "one half", "three quarters")
    if words[-1] in _FRACTION_WORDS or (words[-1].endswith('s') and words[-1][:-1] in _FRACTION_WORDS):
        frac_word = words[-1][:-1] if words[-1].endswith('s') else words[-1]
        denom = _FRACTION_WORDS.get(frac_word)
        if denom:
            numerator_words = words[:-1]
            if not numerator_words:
                numerator = 1
            else:
                num_str = _parse_word_number(' '.join(numerator_words))
                numerator = int(num_str) if num_str and num_str.isdigit() else None
            if numerator is not None:
                result = numerator / denom
                return str(int(result)) if result == int(result) else str(round(result, 6)).rstrip('0').rstrip('.')

    # Parse compound numbers
    total = 0
    current = 0

    for word in words:
        if word in _NUMBER_WORDS:
            current += _NUMBER_WORDS[word]
        elif word == 'hundred':
            current = (current if current else 1) * 100
        elif word == 'thousand':
            current = (current if current else 1) * 1000
            total += current
            current = 0
        elif word == 'million':
            current = (current if current else 1) * 1000000
            total += current
            current = 0
        else:
            # Unknown word - not a valid number
            return None

    total += current
    return str(total) if total > 0 or (len(words) == 1 and words[0] == 'zero') else None


# --- Entity Models ---
class Entity(BaseModel):
    en_name: str = Field(min_length=1, description="Entity name cannot be empty")

    @field_validator('en_name')
    @classmethod
    def normalize_to_proper_noun(cls, v: str) -> str:
        """Normalize entity name to proper noun format (title case)."""
        return smart_title_case(v)


# Build the allowed category literals from the enum
_NUMBER_CATEGORY_VALUES = [e.description for e in NumberCategory]

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
            "Must be a single, lowercase, singular English word — no plurals, no phrases."
        )
    )
    context: str = Field(
        description=(
            "A 1-6 word topic summary so this number is understandable outside the original passage. "
            "Describe the general subject being discussed — someone seeing this entry elsewhere "
            "should immediately understand what this number is about. "
            "Examples: 'tabernacle construction', 'korbanot on sukkot', 'census in wilderness', "
            "'noahs lifespan', 'punishment for theft'."
        )
    )

    @field_validator('number_category')
    @classmethod
    def validate_number_category(cls, v: str) -> str:
        """Ensure number_category is a valid NumberCategory. Falls back to Misc if unknown."""
        valid = {e.description for e in NumberCategory}
        if v not in valid:
            # Try case-insensitive match
            match = next((cat for cat in valid if cat.lower() == v.lower()), None)
            if match:
                return match
            logger.warning(
                f"Unknown number_category '{v}' — falling back to 'Misc'. "
                f"Valid categories: {', '.join(sorted(valid))}"
            )
            return NumberCategory.Misc.description
        return v

    @field_validator('unit')
    @classmethod
    def normalize_unit(cls, v: str) -> str:
        """Normalize unit to lowercase singular noun."""
        v = v.strip().lower()
        # Remove trailing 's' for naive de-pluralization (keeps words like 'class', 'brass')
        if v.endswith('es') and len(v) > 3 and v not in ('incense', 'frankincense', 'bronze'):
            v = v[:-2] if v.endswith('ies') else v[:-1] if v.endswith('ses') or v.endswith('zes') else v[:-2]
        elif v.endswith('s') and not v.endswith('ss') and len(v) > 2:
            v = v[:-1]
        if not v:
            raise ValueError("unit cannot be empty")
        return v

    @field_validator('context')
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
    Person: Optional[List[Entity]] = Field(default_factory=list, description="Individuals AND groups of people (e.g., Moses, The 70 Elders, Children of Israel)")
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
            "unit (normalized singular noun — what is counted/measured), and context (1-6 word topic summary)."
        )
    )
    Animal: Optional[List[Entity]] = Field(default_factory=list, description="Real and mythical animals (e.g., Lion, Eagle, Serpent, Balaam's Donkey)")
    Food: Optional[List[Entity]] = Field(default_factory=list, description="Food items in normalized singular form (e.g., Bread, Manna, Wine)")
    Plant: Optional[List[Entity]] = Field(default_factory=list, description="Plants (edible and inedible) in normalized singular form (e.g., Grape, Fig, Cedar)")

    @field_validator('Number')
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
            valid_numbers.append(NumberEntity(
                en_name=normalized,
                number_category=entity.number_category,
                unit=entity.unit,
                context=entity.context
            ))

        return valid_numbers if valid_numbers else None

    @field_validator('TribeOfIsrael')
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
                logger.warning(
                    f"Filtered invalid tribe: '{entity.en_name}' "
                    f"(not in known tribes list)"
                )

        return valid_tribes if valid_tribes else None

    @field_validator('Nation')
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
                logger.info(
                    f"Auto-corrected demonym: '{entity.en_name}' → '{corrected_name}'"
                )
                corrected.append(Entity(en_name=corrected_name))
            else:
                corrected.append(entity)

        return corrected if corrected else None

    @field_validator('Person', 'Nation')
    @classmethod
    def validate_proper_nouns(cls, v: Optional[List[Entity]], info) -> Optional[List[Entity]]:
        """Filter out generic common nouns from Person and Nation."""
        if not v:
            return v

        # Common words that should NOT be entities (even if capitalized)
        # Note: Person includes both individuals AND named groups
        GENERIC_PERSON_WORDS = {
            # Generic role titles (singular)
            'king', 'priest', 'prophet', 'leader', 'man', 'woman',
            'child', 'servant', 'warrior', 'elder', 'judge', 'scribe',
            'soldier', 'messenger', 'person',
            # Generic plurals
            'people', 'men', 'women', 'children', 'elders',
            # Possessive phrases (these are descriptions, not names)
            'my people', 'his people', 'your people', 'their people',
            'my servants', 'his servants',
            # Indefinite references
            'he who', 'she who', 'they who', 'those who', 'one who',
            'whoever', 'anyone', 'someone'
        }

        # todo remove this poor logic? use Opus to fix up this file file...

        GENERIC_NATION_WORDS = {
            'nation', 'nations', 'people', 'peoples', 'enemy', 'enemies',
            'army', 'armies', 'kingdom', 'kingdoms', 'tribe', 'tribes'
        }

        generic_words = GENERIC_PERSON_WORDS if info.field_name == 'Person' else GENERIC_NATION_WORDS

        valid_entities = []
        filtered_count = 0

        for entity in v:
            # Check if it's a generic word (case-insensitive)
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

    @model_validator(mode='after')
    def exclude_from_symbol_if_in_other_categories(self):
        """
        If an entity appears in Animal, Food, or Plant, it should NOT appear in Symbol.
        Remove such entities from Symbol.
        """
        if not self.Symbol:
            return self

        # Collect all entity names from Animal, Food, Plant
        excluded_names = set()
        for category in ['Animal', 'Food', 'Plant']:
            entity_list = getattr(self, category, None)
            if entity_list:
                excluded_names.update(e.en_name.lower() for e in entity_list)

        if not excluded_names:
            return self

        # Filter Symbol list
        original_count = len(self.Symbol)
        self.Symbol = [
            entity for entity in self.Symbol
            if entity.en_name.lower() not in excluded_names
        ]

        removed_count = original_count - len(self.Symbol)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} entities from Symbol (already in Animal/Food/Plant)")

        if not self.Symbol:
            self.Symbol = None

        return self

    @model_validator(mode='after')
    def ensure_entity_overlap(self):
        """
        Auto-correct entity classification based on priority rules:
        - TribeOfIsrael entities should also appear in Person (tribes are named after people)
        - This ensures relationships like childOfFather, childOfMother, bornIn work for tribe patriarchs
        """
        # Ensure TribeOfIsrael entities are also in Person
        if self.TribeOfIsrael:
            # Initialize Person list if None or empty
            if not self.Person:
                self.Person = []

            existing_persons = {e.en_name.lower() for e in self.Person}

            for tribe_entity in self.TribeOfIsrael:
                if tribe_entity.en_name.lower() not in existing_persons:
                    self.Person.append(Entity(en_name=tribe_entity.en_name))
                    existing_persons.add(tribe_entity.en_name.lower())  # Avoid duplicates in same run
                    logger.warning(  # Changed to WARNING so it shows up
                        f"Auto-added '{tribe_entity.en_name}' to Person "
                        f"(was only in TribeOfIsrael)"
                    )

        return self

    @model_validator(mode='after')
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

    # @model_validator(mode='after')
    # def auto_classify_tribes(self):
    #     """Automatically move tribes from other categories to TribeOfIsrael."""
    #     if not self.TribeOfIsrael:
    #         self.TribeOfIsrael = []
    #
    #     moved_count = 0
    #
    #     # Check all entity categories
    #     for category in ['Person', 'Place', 'Nation', 'Symbol']:
    #         entity_list = getattr(self, category, None)
    #         if not entity_list:
    #             continue
    #
    #         remaining = []
    #         for entity in entity_list:
    #             # Check if this entity is actually a tribe
    #             if entity.en_name.lower() in TRIBES_OF_ISRAEL:
    #                 # Move to TribeOfIsrael
    #                 if entity not in self.TribeOfIsrael:
    #                     self.TribeOfIsrael.append(entity)
    #                     moved_count += 1
    #                     logger.info(
    #                         f"Auto-corrected: Moved '{entity.en_name}' "
    #                         f"from {category} to TribeOfIsrael"
    #                     )
    #             else:
    #                 remaining.append(entity)
    #
    #         # Update the category with remaining entities
    #         setattr(self, category, remaining if remaining else None)
    #
    #     # Deduplicate TribeOfIsrael (in case of duplicates)
    #     if self.TribeOfIsrael:
    #         seen = set()
    #         unique_tribes = []
    #         for tribe in self.TribeOfIsrael:
    #             if tribe.en_name.lower() not in seen:
    #                 unique_tribes.append(tribe)
    #                 seen.add(tribe.en_name.lower())
    #         self.TribeOfIsrael = unique_tribes if unique_tribes else None
    #
    #     if moved_count > 0:
    #         logger.info(f"Auto-corrected {moved_count} tribe classifications")
    #
    #     return self

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

        # Exact match
        if term in all_entities:
            return term

        # Case-insensitive match
        name_map = self.get_all_entity_names_lower()
        term_lower = term.lower()
        if term_lower in name_map:
            return name_map[term_lower]

        # Try removing common plural suffixes
        for suffix in ('s', 'es', 'ies'):
            if term_lower.endswith(suffix):
                singular = term_lower[:-len(suffix)]
                if suffix == 'ies':
                    singular += 'y'  # 'ies' -> 'y' (e.g., 'berries' -> 'berry')
                if singular in name_map:
                    return name_map[singular]

        return None

    def get_entities_by_type(self, entity_type: str) -> Set[str]:
        """Get entity names for a specific type."""
        entity_list = getattr(self, entity_type, None)
        return {e.en_name for e in entity_list} if entity_list else set()


# --- Relationship Models ---
class Relation(BaseModel):
    term1: str = Field(min_length=1, description="Subject (e.g., Student, Child, Sibling A)")
    term2: str = Field(min_length=1, description="Object (e.g., Teacher, Parent, Sibling B)")

    @field_validator('term1', 'term2')
    @classmethod
    def normalize_terms(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Relation terms cannot be empty or whitespace")
        return smart_title_case(v)  # Match Entity normalization


class Relationships(BaseModel):
    # Person/Group → Person/Group
    studiedFrom: Optional[List[Relation]] = Field(default_factory=list)
    childOfFather: Optional[List[Relation]] = Field(default_factory=list)
    childOfMother: Optional[List[Relation]] = Field(default_factory=list)
    spouseOf: Optional[List[Relation]] = Field(default_factory=list)
    descendantOf: Optional[List[Relation]] = Field(default_factory=list)
    spokeWith: Optional[List[Relation]] = Field(default_factory=list)
    disagreedWith: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group → Place
    bornIn: Optional[List[Relation]] = Field(default_factory=list)
    diedIn: Optional[List[Relation]] = Field(default_factory=list)
    visited: Optional[List[Relation]] = Field(default_factory=list)
    prayedAt: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group → Place
    associatedWithPlace: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group → TribeOfIsrael
    personToTribeOfIsrael: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group → Nation
    personBelongsToNation: Optional[List[Relation]] = Field(default_factory=list)

    # Nation → Nation
    EnemyOf: Optional[List[Relation]] = Field(default_factory=list)
    AllyOf: Optional[List[Relation]] = Field(default_factory=list)

    # Place → Nation
    placeToNation: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group → {anything}
    prophesiedAbout: Optional[List[Relation]] = Field(default_factory=list)

    # {anything} → {anything}
    comparedTo: Optional[List[Relation]] = Field(default_factory=list)
    contrastedWith: Optional[List[Relation]] = Field(default_factory=list)
    AliasOf: Optional[List[Relation]] = Field(default_factory=list)


# --- Root Response ---
class ExtractionResult(BaseModel):
    en_summary: str = Field(
        min_length=1,
        description=f"Summary in exactly {min_len_summary}-{max_len_summary} words"
    )
    heb_summary: str = Field(
        min_length=1,
        description=f"Hebrew summary in exactly {min_len_summary}-{max_len_summary} words"
    )
    passage_types: List[Literal['LAW', 'STORY', 'PHILOSOPHIC', 'GENEALOGY', 'PROPHECY']] = Field(
        min_length=1,
        description="At least one passage type required"
    )
    Entities: Entities
    Rel: Optional[Relationships] = Field(default_factory=Relationships)

    @field_validator('en_summary', 'heb_summary')
    @classmethod
    def validate_word_count(cls, v: str, info) -> str:
        """Ensure summary is mix_len_summary - max_len_summary words. Reject if out of range."""
        words = v.strip().split()
        word_count = len(words)

        if word_count < min_len_summary:
            raise ValueError(
                f"{info.field_name} must be {min_len_summary}-{max_len_summary} words, got {word_count}: '{v}'. "
                f"Model should generate complete summaries within word limit."
            )

        if word_count > max_len_summary:
            raise ValueError(
                f"{info.field_name} must be {min_len_summary}-{max_len_summary}, got {word_count}: '{v}'. "
                f"Model should generate complete summaries within word limit."
            )

        return v.strip()

    @field_validator('passage_types')
    @classmethod
    def validate_unique_passage_types(cls, v: List[str]) -> List[str]:
        """Remove duplicate passage types."""
        unique = list(dict.fromkeys(v))  # Preserve order
        if len(unique) < len(v):
            logger.warning(f"Removed duplicate passage types: {v} -> {unique}")
        return unique

    @model_validator(mode='after')
    def filter_invalid_relationships(self):
        """Filter out invalid relationships instead of raising errors."""
        if not self.Rel:
            return self

        all_entities = self.Entities.get_all_entity_names()

        if not all_entities:
            # If no entities, there should be no relationships
            return self

        # Define relationship type constraints
        # Value can be:
        #   (str, str)        → single allowed type pair
        #   [(str, str), ...] → multiple allowed type pairs (any match = valid)
        #   (None, None)      → any entity types allowed
        # Note: "Person" includes both individuals AND groups
        # Note: spokeWith also allows Person↔Animal and Animal↔Animal
        relationship_constraints = {
            # Person/Group ↔ Person/Group
            'studiedFrom': ('Person', 'Person'),
            'childOfFather': ('Person', 'Person'),
            'childOfMother': ('Person', 'Person'),
            'spouseOf': ('Person', 'Person'),
            'descendantOf': ('Person', 'Person'),
            'spokeWith': [('Person', 'Person'), ('Animal', 'Person'), ('Person', 'Animal'), ('Animal', 'Animal')],
            'disagreedWith': ('Person', 'Person'),

            # Person/Group → Place
            'bornIn': ('Person', 'Place'),
            'diedIn': ('Person', 'Place'),
            'visited': ('Person', 'Place'),
            'prayedAt': ('Person', 'Place'),

            # Person/Group → Place (NOT Nation, NOT Symbol)
            'associatedWithPlace': ('Person', 'Place'),

            # Person/Group → TribeOfIsrael
            'personToTribeOfIsrael': ('Person', 'TribeOfIsrael'),

            # Person/Group → Nation
            'personBelongsToNation': ('Person', 'Nation'),

            # Nation → Nation  OR  Person/Group → Person/Group  OR  Person/Group → Nation
            'EnemyOf': [('Nation', 'Nation'), ('Person', 'Person'), ('Person', 'Nation')],
            'AllyOf': [('Nation', 'Nation'), ('Person', 'Person'), ('Person', 'Nation')],

            # Place → Nation
            'placeToNation': ('Place', 'Nation'),

            # Person/Group → {anything}
            'prophesiedAbout': ('Person', None),

            # {anything} → {anything}
            'comparedTo': (None, None),
            'contrastedWith': (None, None),
            'AliasOf': (None, None),
        }

        invalid_count = 0
        corrected_count = 0

        for rel_type, type_constraint in relationship_constraints.items():
            relations = getattr(self.Rel, rel_type, None)
            if not relations:
                continue

            # Normalize to a list of pairs for uniform handling below
            if isinstance(type_constraint, list):
                allowed_pairs = type_constraint
            else:
                allowed_pairs = [type_constraint]  # wrap single pair

            valid_relations = []

            for rel in relations:
                is_valid = True
                reason = None

                # Try to auto-correct terms to match entity names (handles plurals, case differences)
                corrected_term1 = self.Entities.find_matching_entity(rel.term1)
                corrected_term2 = self.Entities.find_matching_entity(rel.term2)

                # Log corrections
                if corrected_term1 and corrected_term1 != rel.term1:
                    logger.info(f"Auto-corrected relationship term: '{rel.term1}' → '{corrected_term1}'")
                    rel.term1 = corrected_term1
                    corrected_count += 1
                if corrected_term2 and corrected_term2 != rel.term2:
                    logger.info(f"Auto-corrected relationship term: '{rel.term2}' → '{corrected_term2}'")
                    rel.term2 = corrected_term2
                    corrected_count += 1

                # Check for self-relationships
                if rel.term1 == rel.term2:
                    is_valid = False
                    reason = f"Self-relationship: {rel.term1}"

                # Check term1 exists in entities
                elif corrected_term1 is None:
                    is_valid = False
                    reason = f"term1 '{rel.term1}' not in entities"

                # Check term2 exists in entities
                elif corrected_term2 is None:
                    is_valid = False
                    reason = f"term2 '{rel.term2}' not in entities"

                # Validate type constraints
                else:
                    # At least one allowed pair must match
                    matched = False
                    for (term1_type, term2_type) in allowed_pairs:
                        # None means "any entity type" - but must still BE an entity
                        term1_ok = (
                                term1_type is None or
                                rel.term1 in self.Entities.get_entities_by_type(term1_type)
                        )
                        term2_ok = (
                                term2_type is None or
                                rel.term2 in self.Entities.get_entities_by_type(term2_type)
                        )
                        if term1_ok and term2_ok:
                            matched = True
                            break

                    if not matched:
                        is_valid = False
                        allowed_str = " or ".join(
                            f"({t1 or 'Any'} → {t2 or 'Any'})" for t1, t2 in allowed_pairs
                        )
                        reason = (
                            f"'{rel.term1}' -> '{rel.term2}' does not match "
                            f"any allowed type pair: {allowed_str}"
                        )

                if is_valid:
                    valid_relations.append(rel)
                else:
                    invalid_count += 1
                    logger.warning(
                        f"Filtered invalid '{rel_type}' relationship: "
                        f"{rel.term1} -> {rel.term2} ({reason})"
                    )

            # Replace with filtered list
            setattr(self.Rel, rel_type, valid_relations if valid_relations else None)

        if corrected_count > 0:
            logger.info(f"Auto-corrected {corrected_count} relationship terms to match entity names")
        if invalid_count > 0:
            logger.info(f"Filtered out {invalid_count} invalid relationships")

        # Deduplicate all relationships (exact duplicates)
        for rel_type in relationship_constraints.keys():
            relations = getattr(self.Rel, rel_type, None)
            if not relations:
                continue

            seen = set()
            unique = []
            for rel in relations:
                key = (rel.term1, rel.term2)
                if key not in seen:
                    unique.append(rel)
                    seen.add(key)

            setattr(self.Rel, rel_type, unique if unique else None)

        return self

    @model_validator(mode='after')
    def deduplicate_symmetric_relationships(self):
        """Deduplicate symmetric relationships (A↔B = B↔A), keeping only one canonical form."""
        if not self.Rel:
            return self

        for rel_type in SYMMETRIC_RELATIONSHIPS:
            relations = getattr(self.Rel, rel_type, None)
            if not relations:
                continue

            seen_pairs = set()
            unique_relations = []

            for rel in relations:
                pair = tuple(sorted([rel.term1, rel.term2]))
                if pair not in seen_pairs:
                    unique_relations.append(rel)
                    seen_pairs.add(pair)
                else:
                    logger.debug(f"Deduplicated {rel_type} pair: {rel.term1} <-> {rel.term2}")

            setattr(self.Rel, rel_type, unique_relations if unique_relations else None)

        return self

    @model_validator(mode='after')
    def clean_descendant_logic(self):
        """Removes descendantOf links that are already defined as childOfFather or childOfMother."""
        if not self.Rel or not self.Rel.descendantOf:
            return self

        # Check if there are any direct parent relationships
        has_father_rels = self.Rel.childOfFather and len(self.Rel.childOfFather) > 0
        has_mother_rels = self.Rel.childOfMother and len(self.Rel.childOfMother) > 0

        if not has_father_rels and not has_mother_rels:
            return self

        # Create a set of (child, parent) tuples for fast lookup from both relationships
        direct_parents = set()
        if self.Rel.childOfFather:
            direct_parents.update((rel.term1, rel.term2) for rel in self.Rel.childOfFather)
        if self.Rel.childOfMother:
            direct_parents.update((rel.term1, rel.term2) for rel in self.Rel.childOfMother)

        # Filter descendantOf to keep only those NOT in direct_parents
        original_count = len(self.Rel.descendantOf)
        self.Rel.descendantOf = [
            rel for rel in self.Rel.descendantOf
            if (rel.term1, rel.term2) not in direct_parents
        ]

        if len(self.Rel.descendantOf) < original_count:
            logger.info(f"Removed redundant descendantOf links duplicated in childOfFather/childOfMother.")

        return self

    @model_validator(mode='after')
    def clean_spokewith_disagreedwith_overlap(self):
        """Removes disagreedWith links that overlap with spokeWith - a pair cannot be in both."""
        if not self.Rel or not self.Rel.spokeWith or not self.Rel.disagreedWith:
            return self

        # Create a set of pairs from spokeWith (both directions since it's symmetric)
        spokewith_pairs = set()
        for rel in self.Rel.spokeWith:
            spokewith_pairs.add((rel.term1, rel.term2))
            spokewith_pairs.add((rel.term2, rel.term1))  # symmetric

        # Filter disagreedWith to keep only those NOT in spokeWith pairs
        original_count = len(self.Rel.disagreedWith)
        self.Rel.disagreedWith = [
            rel for rel in self.Rel.disagreedWith
            if (rel.term1, rel.term2) not in spokewith_pairs
        ]

        removed_count = original_count - len(self.Rel.disagreedWith)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} disagreedWith links that overlap with spokeWith.")

        if not self.Rel.disagreedWith:
            self.Rel.disagreedWith = None

        return self

    @model_validator(mode='after')
    def clean_associated_with_place_logic(self):
        """Removes associatedWithPlace links that are already covered by specific Person→Place relationships."""
        if not self.Rel or not self.Rel.associatedWithPlace:
            return self

        # Collect all existing person-to-place relationships from specific relationship types
        covered_pairs = set()

        for rel_type in PERSON_PLACE_SPECIFIC_RELATIONSHIPS:
            relations = getattr(self.Rel, rel_type, None)
            if relations:
                covered_pairs.update((rel.term1, rel.term2) for rel in relations)

        # Filter associatedWithPlace to keep only those NOT in covered_pairs
        original_count = len(self.Rel.associatedWithPlace)
        self.Rel.associatedWithPlace = [
            rel for rel in self.Rel.associatedWithPlace
            if (rel.term1, rel.term2) not in covered_pairs
        ]

        removed_count = original_count - len(self.Rel.associatedWithPlace)
        if removed_count > 0:
            rel_types_str = '/'.join(PERSON_PLACE_SPECIFIC_RELATIONSHIPS)
            logger.info(f"Removed {removed_count} redundant associatedWithPlace links already covered by {rel_types_str}.")

        # Set to None if empty
        if not self.Rel.associatedWithPlace:
            self.Rel.associatedWithPlace = None

        return self

class FinalResponse(BaseModel):
    res: ExtractionResult