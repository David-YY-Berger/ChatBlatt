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

    def get_entities_by_keys_map(self, keys: List[str]) -> Dict[str, Entity]:
        """
        Batch-fetch entities by key and return a key→Entity mapping.
        Delegates to the existing get_entities_by_keys from EntityMongoMixin.
        """
        if not keys:
            return {}
        entities: List[Entity] = self.get_entities_by_keys(list(keys))
        return {e.key: e for e in entities}
