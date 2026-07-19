# bs"d - lehagdil torah velahadir

from abc import ABC, abstractmethod
from typing import Dict, List

from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Rel import Rel


class GenealogyInterfaceMixin(ABC):
    """
    DB interface mixin for genealogy-specific queries.

    Provides targeted fetching of family relationships and batch entity
    resolution used when building genealogy graphs.
    """

    @abstractmethod
    def get_family_rels_for_entity(self, entity_key: str) -> List[Rel]:
        """
        Fetch only family-type relationships for a given entity key.
        Family rel types: childOfFather, childOfMother, spouseOf.
        Both directions are included (entity as term1 or term2).
        """
        ...

    @abstractmethod
    def get_family_rels_for_entities(self, entity_keys: List[str]) -> List[Rel]:
        """
        Batch-fetch family-type relationships for a whole list of entity keys
        in a single query (entity as term1 or term2, in either direction).
        Family rel types: childOfFather, childOfMother, spouseOf.

        Used to fetch an entire BFS frontier "level" at once when expanding
        an N-degree family graph (e.g. direct family = 1 hop, family of
        family = 2 hops, etc.), instead of querying once per entity.
        """
        ...

    @abstractmethod
    def get_entities_by_keys_map(self, keys: List[str]) -> Dict[str, Entity]:
        """
        Batch-fetch entities by key and return as a dict: key → Entity.
        Keys with no matching entity are omitted from the result.
        """
        ...
