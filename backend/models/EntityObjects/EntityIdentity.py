# bs"d - lehagdil torah velahadir
"""
Entity Identity system.

Each entity type defines its own 'equality' logic to determine whether two
entities refer to the same real-world thing.

Default: same display_en_name (case-insensitive) + same entityType = same entity.

Subclasses override `get_identity_tuple` and `build_existence_query` to define
richer equality semantics (e.g., Person uses parent info to disambiguate).
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass
class PersonFamilyContext:
    """Family relationship context for a single person, extracted from JSON."""
    fathers: Set[str] = field(default_factory=set)   # en_names (lowercased)
    mothers: Set[str] = field(default_factory=set)   # en_names (lowercased)
    spouses: Set[str] = field(default_factory=set)   # en_names (lowercased)


@dataclass
class EntityIdentityContext:
    """
    Holds relationship context needed for entity identity resolution.
    Built from JSON data BEFORE entity insertion, so that identity checks
    can use relationship info that hasn't been persisted to DB yet.
    """
    # Maps person_en_name (lowercased) -> PersonFamilyContext
    person_family: Dict[str, PersonFamilyContext] = field(default_factory=dict)

    def get_person_context(self, en_name: str) -> Optional[PersonFamilyContext]:
        return self.person_family.get(en_name.lower())

    def add_child_of_father(self, child_name: str, father_name: str):
        ctx = self.person_family.setdefault(child_name.lower(), PersonFamilyContext())
        ctx.fathers.add(father_name.lower())

    def add_child_of_mother(self, child_name: str, mother_name: str):
        ctx = self.person_family.setdefault(child_name.lower(), PersonFamilyContext())
        ctx.mothers.add(mother_name.lower())

    def add_spouse(self, person1: str, person2: str):
        ctx1 = self.person_family.setdefault(person1.lower(), PersonFamilyContext())
        ctx1.spouses.add(person2.lower())
        ctx2 = self.person_family.setdefault(person2.lower(), PersonFamilyContext())
        ctx2.spouses.add(person1.lower())

    def are_spouses(self, name1: str, name2: str) -> bool:
        """Check if two people are listed as spouses in this context."""
        ctx = self.person_family.get(name1.lower())
        if ctx and name2.lower() in ctx.spouses:
            return True
        return False


