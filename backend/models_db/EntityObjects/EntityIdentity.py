# bs"d - lehagdil torah velahadir
"""
Entity Identity system.

Each entity type defines its own 'equality' logic to determine whether two
entities refer to the same real-world thing.

Default: same display_en_name (case-insensitive) + same entityType = same entity.

Subclasses override `get_identity_tuple` and `build_existence_query` to define
richer equality semantics (e.g., Person uses parent/family info via
PersonFamilyContext to disambiguate same-named individuals).
"""

from dataclasses import dataclass, field
from typing import Set


@dataclass
class PersonFamilyContext:
    """Family relationship context for a single person, extracted from JSON."""
    fathers: Set[str] = field(default_factory=set)   # en_names (lowercased)
    mothers: Set[str] = field(default_factory=set)   # en_names (lowercased)
    spouses: Set[str] = field(default_factory=set)   # en_names (lowercased)


