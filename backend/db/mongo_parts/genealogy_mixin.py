# bs"d - lehagdil torah velahadir

from typing import Any, Dict, List

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Rel import Rel

# The three rel types that define direct family connections in the DB
_FAMILY_REL_TYPE_VALUES = [
    "childOfFather",
    "childOfMother",
    "spouseOf",
]


class GenealogyMongoMixin:
    """
    MongoDB implementation of GenealogyInterfaceMixin.

    Mixed into DBapiMongoDB alongside RelationshipMongoMixin and EntityMongoMixin,
    so self.get_collection, self._doc_to_rel, and self.get_entities_by_keys
    are all available via the MRO.
    """

    def get_collection(self, collection):
        raise NotImplementedError

    def get_family_rels_for_entity(self, entity_key: str) -> List[Rel]:
        """
        Query the relations collection for all family rels involving entity_key,
        filtering at the DB level to only the three family rel types.
        """
        docs = self.get_collection(CollectionObjs.RELATIONS).find({
            DBOperators.OR: [
                {DBFields.TERM1: entity_key},
                {DBFields.TERM2: entity_key},
            ],
            DBFields.REL_TYPE: {DBOperators.IN: _FAMILY_REL_TYPE_VALUES},
        })
        return [self._doc_to_rel(doc) for doc in docs]

    def get_family_rels_for_entities(self, entity_keys: List[str]) -> List[Rel]:
        """
        Query the relations collection for all family rels involving ANY of the
        given entity_keys (as term1 or term2), in a single round-trip.

        Used to expand a whole BFS "frontier" level at once when building an
        N-degree family graph, instead of issuing one query per entity.
        """
        if not entity_keys:
            return []
        docs = self.get_collection(CollectionObjs.RELATIONS).find({
            DBOperators.OR: [
                {DBFields.TERM1: {DBOperators.IN: list(entity_keys)}},
                {DBFields.TERM2: {DBOperators.IN: list(entity_keys)}},
            ],
            DBFields.REL_TYPE: {DBOperators.IN: _FAMILY_REL_TYPE_VALUES},
        })
        return [self._doc_to_rel(doc) for doc in docs]

    def get_rels_by_type_for_entities(
        self,
        entity_keys: List[str],
        rel_type_values: List[str],
        as_term1: bool = True,
        as_term2: bool = True,
    ) -> List[Rel]:
        """
        Batch-fetch rels of the given types where ANY of entity_keys is term1
        (as_term1) and/or term2 (as_term2), in a single round-trip.
        """
        if not entity_keys or not rel_type_values:
            return []
        keys = list(entity_keys)
        conditions = []
        if as_term1:
            conditions.append({DBFields.TERM1: {DBOperators.IN: keys}})
        if as_term2:
            conditions.append({DBFields.TERM2: {DBOperators.IN: keys}})
        if not conditions:
            return []
        docs = self.get_collection(CollectionObjs.RELATIONS).find({
            DBOperators.OR: conditions,
            DBFields.REL_TYPE: {DBOperators.IN: list(rel_type_values)},
        })
        return [self._doc_to_rel(doc) for doc in docs]

    def get_entities_by_keys_map(self, keys: List[str]) -> Dict[str, Entity]:
        """
        Batch-fetch entities by key and return a key→Entity mapping.
        Delegates to the existing get_entities_by_keys from EntityMongoMixin.
        """
        if not keys:
            return {}
        entities: List[Entity] = self.get_entities_by_keys(list(keys))
        return {e.key: e for e in entities}
