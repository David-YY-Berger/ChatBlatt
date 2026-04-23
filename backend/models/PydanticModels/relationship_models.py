from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.models.PydanticModels.name_utils import smart_title_case


class Relation(BaseModel):
    term1: str = Field(min_length=1, description="Subject (e.g., Student, Child, Sibling A)")
    term2: str = Field(min_length=1, description="Object (e.g., Teacher, Parent, Sibling B)")

    @field_validator("term1", "term2")
    @classmethod
    def normalize_terms(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Relation terms cannot be empty or whitespace")
        return smart_title_case(v)


class Relationships(BaseModel):
    # Person/Group -> Person/Group
    studiedFrom: Optional[List[Relation]] = Field(default_factory=list)
    childOfFather: Optional[List[Relation]] = Field(default_factory=list)
    childOfMother: Optional[List[Relation]] = Field(default_factory=list)
    spouseOf: Optional[List[Relation]] = Field(default_factory=list)
    descendantOf: Optional[List[Relation]] = Field(default_factory=list)
    spokeWith: Optional[List[Relation]] = Field(default_factory=list)
    disagreedWith: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group -> Place
    bornIn: Optional[List[Relation]] = Field(default_factory=list)
    diedIn: Optional[List[Relation]] = Field(default_factory=list)
    visited: Optional[List[Relation]] = Field(default_factory=list)
    prayedAt: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group -> Place
    associatedWithPlace: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group -> TribeOfIsrael
    personToTribeOfIsrael: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group -> Nation
    personBelongsToNation: Optional[List[Relation]] = Field(default_factory=list)

    # Nation -> Nation
    EnemyOf: Optional[List[Relation]] = Field(default_factory=list)
    AllyOf: Optional[List[Relation]] = Field(default_factory=list)

    # Place -> Nation
    placeToNation: Optional[List[Relation]] = Field(default_factory=list)

    # Person/Group -> {anything}
    prophesiedAbout: Optional[List[Relation]] = Field(default_factory=list)

    # {anything} -> {anything}
    comparedTo: Optional[List[Relation]] = Field(default_factory=list)
    contrastedWith: Optional[List[Relation]] = Field(default_factory=list)
    AliasOf: Optional[List[Relation]] = Field(default_factory=list)


__all__ = ["Relation", "Relationships"]

