from typing import List, Optional, Literal, Set
from pydantic import BaseModel, Field, field_validator, model_validator
import logging

logger = logging.getLogger(__name__)


# --- Entity Models ---
class Entity(BaseModel):
    en_name: str = Field(min_length=1, description="Entity name cannot be empty")


class Entities(BaseModel):
    Person: Optional[List[Entity]] = Field(default_factory=list)
    Place: Optional[List[Entity]] = Field(default_factory=list)
    TribeOfIsrael: Optional[List[Entity]] = Field(default_factory=list)
    Nation: Optional[List[Entity]] = Field(default_factory=list)
    Symbol: Optional[List[Entity]] = Field(default_factory=list)

    def get_all_entity_names(self) -> Set[str]:
        """Helper to get all entity names across all categories."""
        names = set()
        for entity_list in [self.Person, self.Place, self.TribeOfIsrael,
                            self.Nation, self.Symbol]:
            if entity_list:
                names.update(e.en_name for e in entity_list)
        return names

    def get_entities_by_type(self, entity_type: str) -> Set[str]:
        """Get entity names for a specific type."""
        entity_list = getattr(self, entity_type, None)
        return {e.en_name for e in entity_list} if entity_list else set()


# --- Relationship Models ---
class Relation(BaseModel):
    term1: str = Field(min_length=1, description="First entity in relationship")
    term2: str = Field(min_length=1, description="Second entity in relationship")

    @field_validator('term1', 'term2')
    @classmethod
    def validate_terms_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Relation terms cannot be empty or whitespace")
        return v.strip()


class Relationships(BaseModel):
    # Person → Person
    studiedFrom: Optional[List[Relation]] = Field(default_factory=list)
    siblingWith: Optional[List[Relation]] = Field(default_factory=list)
    childOf: Optional[List[Relation]] = Field(default_factory=list)
    spouseOf: Optional[List[Relation]] = Field(default_factory=list)
    descendantOf: Optional[List[Relation]] = Field(default_factory=list)

    # Person → Place
    bornIn: Optional[List[Relation]] = Field(default_factory=list)
    diedIn: Optional[List[Relation]] = Field(default_factory=list)
    residedIn: Optional[List[Relation]] = Field(default_factory=list)
    visited: Optional[List[Relation]] = Field(default_factory=list)

    # Person → TribeOfIsrael
    personToTribeOfIsrael: Optional[List[Relation]] = Field(default_factory=list)

    # Person → Nation
    personBelongsToNation: Optional[List[Relation]] = Field(default_factory=list)

    # Nation → Nation
    EnemyOf: Optional[List[Relation]] = Field(default_factory=list)
    AllyOf: Optional[List[Relation]] = Field(default_factory=list)

    # Place → Nation
    placeToNation: Optional[List[Relation]] = Field(default_factory=list)

    # {anything} → Symbol
    comparedTo: Optional[List[Relation]] = Field(default_factory=list)
    contrastedWith: Optional[List[Relation]] = Field(default_factory=list)

    # {anything} → {anything}
    alias: Optional[List[Relation]] = Field(default_factory=list)
    aliasFromSages: Optional[List[Relation]] = Field(default_factory=list)


# --- Root Response ---
class ExtractionResult(BaseModel):
    en_summary: str = Field(
        min_length=1,
        description="Summary in exactly 4-10 words"
    )
    heb_summary: str = Field(
        min_length=1,
        description="Hebrew summary in exactly 4-10 words"
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
        """Ensure summary is 4-10 words. If invalid, truncate or pad."""
        words = v.strip().split()
        word_count = len(words)

        if word_count < 4:
            logger.warning(f"{info.field_name} has only {word_count} words (min 4): '{v}'")
            # Pad with generic word if too short - but accept it
            return v.strip()

        if word_count > 10:
            logger.warning(f"{info.field_name} has {word_count} words (max 10): '{v}'. Truncating.")
            # Truncate to 10 words
            return ' '.join(words[:10])

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
        relationship_constraints = {
            # Person → Person
            'studiedFrom': ('Person', 'Person'),
            'siblingWith': ('Person', 'Person'),
            'childOf': ('Person', 'Person'),
            'spouseOf': ('Person', 'Person'),
            'descendantOf': ('Person', 'Person'),

            # Person → Place
            'bornIn': ('Person', 'Place'),
            'diedIn': ('Person', 'Place'),
            'residedIn': ('Person', 'Place'),
            'visited': ('Person', 'Place'),

            # Person → TribeOfIsrael
            'personToTribeOfIsrael': ('Person', 'TribeOfIsrael'),

            # Person → Nation
            'personBelongsToNation': ('Person', 'Nation'),

            # Nation → Nation
            'EnemyOf': ('Nation', 'Nation'),
            'AllyOf': ('Nation', 'Nation'),

            # Place → Nation
            'placeToNation': ('Place', 'Nation'),

            # {anything} → Symbol
            'comparedTo': (None, 'Symbol'),
            'contrastedWith': (None, 'Symbol'),

            # {anything} → {anything} (no constraints)
            'alias': (None, None),
            'aliasFromSages': (None, None),
        }

        invalid_count = 0

        for rel_type, (term1_type, term2_type) in relationship_constraints.items():
            relations = getattr(self.Rel, rel_type, None)
            if not relations:
                continue

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
                elif term1_type:
                    term1_entities = self.Entities.get_entities_by_type(term1_type)
                    if rel.term1 not in term1_entities:
                        is_valid = False
                        reason = f"term1 '{rel.term1}' not a {term1_type}"

                if is_valid and term2_type:
                    term2_entities = self.Entities.get_entities_by_type(term2_type)
                    if rel.term2 not in term2_entities:
                        is_valid = False
                        reason = f"term2 '{rel.term2}' not a {term2_type}"

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

        return self

    @model_validator(mode='after')
    def filter_asymmetric_relationships(self):
        """Filter out asymmetric sibling/spouse relationships."""
        if not self.Rel:
            return self

        # Handle siblingWith symmetry
        if self.Rel.siblingWith:
            siblings = {}
            for rel in self.Rel.siblingWith:
                siblings.setdefault(rel.term1, set()).add(rel.term2)
                siblings.setdefault(rel.term2, set()).add(rel.term1)

            valid_siblings = []
            seen_pairs = set()

            for rel in self.Rel.siblingWith:
                pair = tuple(sorted([rel.term1, rel.term2]))
                if pair in seen_pairs:
                    continue

                # Check if symmetric
                if rel.term2 in siblings.get(rel.term1, set()) and \
                        rel.term1 in siblings.get(rel.term2, set()):
                    valid_siblings.append(rel)
                    seen_pairs.add(pair)
                else:
                    logger.warning(
                        f"Filtered asymmetric sibling: {rel.term1} <-> {rel.term2}"
                    )

            self.Rel.siblingWith = valid_siblings if valid_siblings else None

        # Handle spouseOf symmetry
        if self.Rel.spouseOf:
            spouses = {}
            for rel in self.Rel.spouseOf:
                spouses.setdefault(rel.term1, set()).add(rel.term2)
                spouses.setdefault(rel.term2, set()).add(rel.term1)

            valid_spouses = []
            seen_pairs = set()

            for rel in self.Rel.spouseOf:
                pair = tuple(sorted([rel.term1, rel.term2]))
                if pair in seen_pairs:
                    continue

                # Check if symmetric
                if rel.term2 in spouses.get(rel.term1, set()) and \
                        rel.term1 in spouses.get(rel.term2, set()):
                    valid_spouses.append(rel)
                    seen_pairs.add(pair)
                else:
                    logger.warning(
                        f"Filtered asymmetric spouse: {rel.term1} <-> {rel.term2}"
                    )

            self.Rel.spouseOf = valid_spouses if valid_spouses else None

        return self


class FinalResponse(BaseModel):
    res: ExtractionResult