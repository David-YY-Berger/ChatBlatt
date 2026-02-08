from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Entity Models ---
class Entity(BaseModel):
    en_name: str

class Entities(BaseModel):
    Person: Optional[List[Entity]] = Field(default_factory=list)
    Place: Optional[List[Entity]] = Field(default_factory=list)
    TribeOfIsrael: Optional[List[Entity]] = Field(default_factory=list)
    Nation: Optional[List[Entity]] = Field(default_factory=list)
    Symbol: Optional[List[Entity]] = Field(default_factory=list)

# --- Relationship Models ---
class Relation(BaseModel):
    term1: str
    term2: str

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
    en_summary: str = Field(description="4-10 words summary")
    heb_summary: str = Field(description="4-10 words Hebrew summary")
    passage_types: List[Literal['LAW', 'STORY', 'PHILOSOPHIC', 'GENEALOGY', 'PROPHECY']]
    Entities: Entities
    Rel: Optional[Relationships] = Field(default_factory=list)

class FinalResponse(BaseModel):
    res: ExtractionResult