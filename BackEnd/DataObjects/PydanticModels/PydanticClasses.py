from typing import List, Optional, Literal, Set
from pydantic import BaseModel, Field, field_validator, model_validator


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

    @model_validator(mode='after')
    def validate_terms_different(self):
        """Ensure term1 and term2 are different (no self-relationships)."""
        if self.term1 == self.term2:
            raise ValueError(f"Self-relationship not allowed: {self.term1}")
        return self


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
        max_length=100,
        description="4-10 words summary"
    )
    heb_summary: str = Field(
        min_length=1,
        max_length=100,
        description="4-10 words Hebrew summary"
    )
    passage_types: List[Literal['LAW', 'STORY', 'PHILOSOPHIC', 'GENEALOGY', 'PROPHECY']] = Field(
        min_length=1,
        description="At least one passage type required"
    )
    Entities: Entities
    Rel: Optional[Relationships] = Field(default_factory=Relationships)

    @field_validator('passage_types')
    @classmethod
    def validate_unique_passage_types(cls, v: List[str]) -> List[str]:
        """Ensure no duplicate passage types."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate passage types not allowed")
        return v

    @model_validator(mode='after')
    def validate_relationships_reference_entities(self):
        """Ensure all relationship terms reference actual entities."""
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

        if self.Rel:
            for rel_type, (term1_type, term2_type) in relationship_constraints.items():
                relations = getattr(self.Rel, rel_type, None)
                if not relations:
                    continue

                for rel in relations:
                    # Check term1 exists in entities
                    if rel.term1 not in all_entities:
                        raise ValueError(
                            f"Relationship '{rel_type}': term1 '{rel.term1}' "
                            f"not found in entities"
                        )

                    # Check term2 exists in entities
                    if rel.term2 not in all_entities:
                        raise ValueError(
                            f"Relationship '{rel_type}': term2 '{rel.term2}' "
                            f"not found in entities"
                        )

                    # Validate type constraints
                    if term1_type:
                        term1_entities = self.Entities.get_entities_by_type(term1_type)
                        if rel.term1 not in term1_entities:
                            raise ValueError(
                                f"Relationship '{rel_type}': term1 '{rel.term1}' "
                                f"must be a {term1_type} entity"
                            )

                    if term2_type:
                        term2_entities = self.Entities.get_entities_by_type(term2_type)
                        if rel.term2 not in term2_entities:
                            raise ValueError(
                                f"Relationship '{rel_type}': term2 '{rel.term2}' "
                                f"must be a {term2_type} entity"
                            )

        return self

    @model_validator(mode='after')
    def validate_symmetric_relationships(self):
        """Ensure symmetric relationships are properly mirrored."""
        if not self.Rel:
            return self

        # siblingWith and spouseOf should be symmetric
        if self.Rel.siblingWith:
            siblings = {}
            for rel in self.Rel.siblingWith:
                siblings.setdefault(rel.term1, set()).add(rel.term2)
                siblings.setdefault(rel.term2, set()).add(rel.term1)

            # Verify symmetry
            for person, sibling_set in siblings.items():
                for sibling in sibling_set:
                    if person not in siblings.get(sibling, set()):
                        raise ValueError(
                            f"Asymmetric sibling relationship: "
                            f"{person} ↔ {sibling}"
                        )

        if self.Rel.spouseOf:
            spouses = {}
            for rel in self.Rel.spouseOf:
                spouses.setdefault(rel.term1, set()).add(rel.term2)
                spouses.setdefault(rel.term2, set()).add(rel.term1)

            # Verify symmetry
            for person, spouse_set in spouses.items():
                for spouse in spouse_set:
                    if person not in spouses.get(spouse, set()):
                        raise ValueError(
                            f"Asymmetric spouse relationship: "
                            f"{person} ↔ {spouse}"
                        )

        return self


class FinalResponse(BaseModel):
    res: ExtractionResult