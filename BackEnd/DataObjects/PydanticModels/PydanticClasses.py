from typing import List, Optional, Literal, Set
from pydantic import BaseModel, Field, field_validator, model_validator
import logging

logger = logging.getLogger(__name__)

# --- Global Constants ---
TRIBES_OF_ISRAEL = {
    'reuben', 'simeon', 'levi', 'judah', 'dan', 'naphtali',
    'gad', 'asher', 'issachar', 'zebulun', 'joseph', 'benjamin',
    'ephraim', 'manasseh'
}

# Entity category names - used for validation and iteration
ENTITY_CATEGORIES = ('Person', 'Place', 'TribeOfIsrael', 'Nation', 'Symbol')

# Symmetric relationships where (A, B) == (B, A)
SYMMETRIC_RELATIONSHIPS = ('spouseOf', 'spokeWith', 'EnemyOf', 'AllyOf', 'AliasOf')

max_len_summary: int = 10
min_len_summary: int = 4

# --- Entity Models ---
class Entity(BaseModel):
    en_name: str = Field(min_length=1, description="Entity name cannot be empty")

    @field_validator('en_name')
    @classmethod
    def normalize_to_proper_noun(cls, v: str) -> str:
        """Normalize entity name to proper noun format (title case)."""
        return v.strip().title()


class Entities(BaseModel):
    Person: Optional[List[Entity]] = Field(default_factory=list, description="Individuals AND groups of people (e.g., Moses, The 70 Elders, Children of Israel)")
    Place: Optional[List[Entity]] = Field(default_factory=list)
    TribeOfIsrael: Optional[List[Entity]] = Field(default_factory=list)
    Nation: Optional[List[Entity]] = Field(default_factory=list)
    Symbol: Optional[List[Entity]] = Field(default_factory=list)

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

    @field_validator('Person', 'Nation')
    @classmethod
    def validate_proper_nouns(cls, v: Optional[List[Entity]], info) -> Optional[List[Entity]]:
        """Filter out generic common nouns from Person and Nation."""
        if not v:
            return v

        # Common words that should NOT be entities (even if capitalized)
        # Note: Person includes both individuals AND named groups
        GENERIC_PERSON_WORDS = {
            'king', 'priest', 'prophet', 'leader', 'man', 'woman',
            'child', 'servant', 'warrior', 'elder', 'judge', 'scribe',
            'people', 'person', 'soldier', 'messenger', 'angel',
            'group', 'elders', 'children', 'men', 'women'  # generic group terms
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
    def ensure_entity_overlap(self):
        """
        Auto-correct entity classification based on priority rules:
        - TribeOfIsrael entities should also appear in Person (tribes are named after people)
        - This ensures relationships like childOf, bornIn work for tribe patriarchs
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
        return v.strip().title()  # Match Entity normalization


class Relationships(BaseModel):
    # Person/Group → Person/Group
    studiedFrom: Optional[List[Relation]] = Field(default_factory=list)
    childOf: Optional[List[Relation]] = Field(default_factory=list)
    spouseOf: Optional[List[Relation]] = Field(default_factory=list)
    descendantOf: Optional[List[Relation]] = Field(default_factory=list)
    spokeWith: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group → Place
    bornIn: Optional[List[Relation]] = Field(default_factory=list)
    diedIn: Optional[List[Relation]] = Field(default_factory=list)
    visited: Optional[List[Relation]] = Field(default_factory=list)

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
        relationship_constraints = {
            # Person/Group → Person/Group
            'studiedFrom': ('Person', 'Person'),
            'childOf': ('Person', 'Person'),
            'spouseOf': ('Person', 'Person'),
            'descendantOf': ('Person', 'Person'),
            'spokeWith': ('Person', 'Person'),

            # Person/Group → Place
            'bornIn': ('Person', 'Place'),
            'diedIn': ('Person', 'Place'),
            'visited': ('Person', 'Place'),

            # Person/Group → TribeOfIsrael
            'personToTribeOfIsrael': ('Person', 'TribeOfIsrael'),

            # Person/Group → Nation
            'personBelongsToNation': ('Person', 'Nation'),

            # Nation → Nation  OR  Person/Group → Person/Group
            'EnemyOf': [('Nation', 'Nation'), ('Person', 'Person')],
            'AllyOf': [('Nation', 'Nation'), ('Person', 'Person')],

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

                # Check for self-relationships
                if rel.term1 == rel.term2:
                    is_valid = False
                    reason = f"Self-relationship: {rel.term1}"

                # Check term1 exists in entities
                elif rel.term1 not in all_entities:
                    is_valid = False
                    reason = f"term1 '{rel.term1}' not in entities"

                # Check term2 exists in entities
                elif rel.term2 not in all_entities:
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
        """Removes descendantOf links that are already defined as childOf."""
        if not self.Rel or not self.Rel.childOf or not self.Rel.descendantOf:
            return self

        # Create a set of (child, parent) tuples for fast lookup
        direct_parents = {
            (rel.term1, rel.term2) for rel in self.Rel.childOf
        }

        # Filter descendantOf to keep only those NOT in direct_parents
        original_count = len(self.Rel.descendantOf)
        self.Rel.descendantOf = [
            rel for rel in self.Rel.descendantOf
            if (rel.term1, rel.term2) not in direct_parents
        ]

        if len(self.Rel.descendantOf) < original_count:
            logger.info(f"Removed redundant descendantOf links duplicated in childOf.")

        return self

class FinalResponse(BaseModel):
    res: ExtractionResult