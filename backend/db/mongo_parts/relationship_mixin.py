from typing import Any, Dict, List, Optional, Tuple

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.models.Rel import Rel


class RelationshipMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    def is_rel_exists(self, key: str) -> bool:
        return self.get_collection(CollectionObjs.RELATIONS).find_one({DBFields.KEY: key}) is not None

    def insert_rel(self, rel: Rel) -> str:
        data = rel.to_db_dict()
        data[DBFields.REL_TYPE] = rel.rel_type.value
        result = self.get_collection(CollectionObjs.RELATIONS).insert_one(data)
        return str(result.inserted_id)

    def update_rel(self, rel: Rel) -> int:
        data = rel.to_db_dict()
        data[DBFields.REL_TYPE] = rel.rel_type.value
        key = data.pop(DBFields.KEY)
        result = self.get_collection(CollectionObjs.RELATIONS).update_one(
            {DBFields.KEY: key},
            {DBOperators.SET: data},
        )
        return result.modified_count

    def get_rel_by_key(self, key: str) -> Optional[Rel]:
        doc = self.get_collection(CollectionObjs.RELATIONS).find_one({DBFields.KEY: key})
        if doc is None:
            return None
        return self._doc_to_rel(doc)

    def get_rels_by_keys(self, keys: List[str]) -> List[Rel]:
        docs = self.get_collection(CollectionObjs.RELATIONS).find({DBFields.KEY: {DBOperators.IN: keys}})
        return [self._doc_to_rel(doc) for doc in docs]

    def get_rels_for_entity(self, entity_key: str) -> List[Rel]:
        docs = self.get_collection(CollectionObjs.RELATIONS).find(
            {
                DBOperators.OR: [
                    {DBFields.TERM1: entity_key},
                    {DBFields.TERM2: entity_key},
                ]
            }
        )
        return [self._doc_to_rel(doc) for doc in docs]

    def get_all_rels(self) -> List[Rel]:
        docs = self.get_collection(CollectionObjs.RELATIONS).find({})
        return [self._doc_to_rel(doc) for doc in docs]

    def insert_rels_bulk(self, rels: List[Rel]) -> int:
        if not rels:
            return 0
        docs = []
        for rel in rels:
            data = rel.to_db_dict()
            data[DBFields.REL_TYPE] = rel.rel_type.value
            docs.append(data)
        result = self.get_collection(CollectionObjs.RELATIONS).insert_many(docs)
        return len(result.inserted_ids)

    def upsert_rels_bulk(self, rels: List[Rel]) -> Tuple[int, int]:
        from pymongo import UpdateOne

        if not rels:
            return (0, 0)

        operations = []
        for rel in rels:
            data = rel.to_db_dict()
            data[DBFields.REL_TYPE] = rel.rel_type.value
            operations.append(UpdateOne({DBFields.KEY: rel.key}, {DBOperators.SET: data}, upsert=True))

        result = self.get_collection(CollectionObjs.RELATIONS).bulk_write(operations)
        return (result.upserted_count, result.modified_count)

    def _doc_to_rel(self, doc: Dict[str, Any]) -> Rel:
        from backend.models.Enums import RelType

        doc = {k: v for k, v in doc.items() if k != "_id"}

        rel_type_value = doc.get(DBFields.REL_TYPE)
        doc[DBFields.REL_TYPE] = RelType(rel_type_value)

        return Rel.model_validate(doc)

