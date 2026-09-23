# bs"d - lehagdil torah velahadir
"""
Entity Identity system.

Each entity type defines its own 'equality' logic to determine whether two
entities refer to the same real-world thing.

Default: same display_en_name (case-insensitive) + same entityType = same entity
(see Entity.get_identity_tuple / Entity.build_existence_query; subclasses may override).

Person is the exception: different people often share a display_en_name (e.g. two
kings named Joash), so a Person mention extracted from a source is resolved against
the DB by the pipeline's PersonDisambiguator, using the evidence that source gives
about the mention (PersonSourceContext below).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set

from backend.models_db.Enums import RelType, SourceType
from backend.models_db.SourceClasses.SourceClass import SourceClass


@dataclass(frozen=True)
class PassageRelation:
    """One relationship, in the current source, between the Person being resolved and another entity."""
    rel_type: RelType
    person_is_term1: bool  # True: person --rel_type--> other; False: other --rel_type--> person
    other_name: str        # the other entity's en_name, lowercased


@dataclass
class PersonSourceContext:
    """
    Everything the current source says about one Person mention. A freshly extracted
    mention has no metadata of its own, so this is all the evidence there is for
    deciding which existing same-named Person (if any) it refers to.
    """
    source_key: str  # e.g. "TN_II Kings_0_12:1-22" - encodes the source type and book
    relations: List[PassageRelation] = field(default_factory=list)
    source_entity_names: Set[str] = field(default_factory=set)  # lowercased en_names of the OTHER entities in the source

    @property
    def source_type(self) -> Optional[SourceType]:
        return SourceClass.get_src_type_from_key(self.source_key)

    @property
    def fathers(self) -> Set[str]:
        return {r.other_name for r in self.relations if r.rel_type == RelType.childOfFather and r.person_is_term1}

    @property
    def mothers(self) -> Set[str]:
        return {r.other_name for r in self.relations if r.rel_type == RelType.childOfMother and r.person_is_term1}

