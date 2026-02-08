from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# todo refactor to diff files?

# --- Entity Models ---
class Entity(BaseModel):
    en_name: str

class Entities(BaseModel):
    Person: Optional[List[Entity]] = None
    Place: Optional[List[Entity]] = None
    TribeOfIsrael: Optional[List[Entity]] = None
    Nation: Optional[List[Entity]] = None
    Symbol: Optional[List[Entity]] = None

# --- Relationship Models ---
class Relation(BaseModel):
    term1: str
    term2: str

class Relationships(BaseModel):
    # Person → Person
    studiedFrom: Optional[List[Relation]] = None
    siblingWith: Optional[List[Relation]] = None
    childOf: Optional[List[Relation]] = None
    spouseOf: Optional[List[Relation]] = None
    descendantOf: Optional[List[Relation]] = None

    # Person → Place
    bornIn: Optional[List[Relation]] = None
    diedIn: Optional[List[Relation]] = None
    residedIn: Optional[List[Relation]] = None
    visited: Optional[List[Relation]] = None

    # Person → TribeOfIsrael
    personToTribeOfIsrael: Optional[List[Relation]] = None

    # Person → Nation
    personBelongsToNation: Optional[List[Relation]] = None

    # Nation → Nation
    EnemyOf: Optional[List[Relation]] = None
    AllyOf: Optional[List[Relation]] = None

    # Place → Nation
    placeToNation: Optional[List[Relation]] = None

    # {anything} → Symbol
    comparedTo: Optional[List[Relation]] = None
    contrastedWith: Optional[List[Relation]] = None

    # {anything} → {anything}
    alias: Optional[List[Relation]] = None
    aliasFromSages: Optional[List[Relation]] = None

# --- Root Response ---
class ExtractionResult(BaseModel):
    en_summary: str = Field(description="4-10 words summary")
    heb_summary: str = Field(description="4-10 words Hebrew summary")
    passage_types: List[Literal['LAW', 'STORY', 'PHILOSOPHIC', 'GENEALOGY', 'PROPHECY']]
    Entities: Entities
    Rel: Optional[Relationships] = None

class FinalResponse(BaseModel):
    res: ExtractionResult