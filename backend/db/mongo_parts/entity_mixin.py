from typing import Any, Dict, List, Optional, Tuple

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.models.EntityObjects.Entity import Entity
from backend.models.Enums import EntityType


class EntityMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    def is_entity_exists(self, key: str) -> bool:
        return self.get_collection(CollectionObjs.ENTITIES).find_one({DBFields.KEY: key}) is not None

    def insert_entity(self, entity: Entity) -> str:
        data = entity.to_db_dict()
        data[DBFields.ENTITY_TYPE] = entity.entityType.value
        result = self.get_collection(CollectionObjs.ENTITIES).insert_one(data)
        return str(result.inserted_id)

    def update_entity(self, entity: Entity) -> int:
        data = entity.to_db_dict()
        data[DBFields.ENTITY_TYPE] = entity.entityType.value
        key = data.pop(DBFields.KEY)
        result = self.get_collection(CollectionObjs.ENTITIES).update_one(
            {DBFields.KEY: key},
            {DBOperators.SET: data},
        )
        return result.modified_count

    def get_entity_by_key(self, key: str) -> Optional[Entity]:
        doc = self.get_collection(CollectionObjs.ENTITIES).find_one({DBFields.KEY: key})
        if doc is None:
            return None
        return self._doc_to_entity(doc)

    def get_entities_by_keys(self, keys: List[str]) -> List[Entity]:
        docs = self.get_collection(CollectionObjs.ENTITIES).find({DBFields.KEY: {DBOperators.IN: keys}})
        return [self._doc_to_entity(doc) for doc in docs]

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        docs = self.get_collection(CollectionObjs.ENTITIES).find({DBFields.ENTITY_TYPE: entity_type.value})
        return [self._doc_to_entity(doc) for doc in docs]

    def get_all_entities(self) -> List[Entity]:
        docs = self.get_collection(CollectionObjs.ENTITIES).find({})
        return [self._doc_to_entity(doc) for doc in docs]

    def search_entities_by_name(self, name: str, entity_type: Optional[EntityType] = None) -> List[Entity]:
        regex_pattern = {DBOperators.REGEX: name, DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE}
        name_query = {
            DBOperators.OR: [
                {DBFields.DISPLAY_EN_NAME: regex_pattern},
                {DBFields.DISPLAY_HEB_NAME: regex_pattern},
                {DBFields.ALL_EN_NAMES: regex_pattern},
                {DBFields.ALL_HEB_NAMES: regex_pattern},
            ]
        }
        query = {DBOperators.AND: [name_query, {DBFields.ENTITY_TYPE: entity_type.value}]} if entity_type else name_query
        docs = self.get_collection(CollectionObjs.ENTITIES).find(query)
        return [self._doc_to_entity(doc) for doc in docs]

    def insert_entities_bulk(self, entities: List[Entity]) -> int:
        if not entities:
            return 0
        docs = []
        for entity in entities:
            data = entity.to_db_dict()
            data[DBFields.ENTITY_TYPE] = entity.entityType.value
            docs.append(data)
        result = self.get_collection(CollectionObjs.ENTITIES).insert_many(docs)
        return len(result.inserted_ids)

    def upsert_entities_bulk(self, entities: List[Entity]) -> Tuple[int, int]:
        from pymongo import UpdateOne

        if not entities:
            return (0, 0)

        operations = []
        for entity in entities:
            data = entity.to_db_dict()
            data[DBFields.ENTITY_TYPE] = entity.entityType.value
            operations.append(UpdateOne({DBFields.KEY: entity.key}, {DBOperators.SET: data}, upsert=True))

        result = self.get_collection(CollectionObjs.ENTITIES).bulk_write(operations)
        return (result.upserted_count, result.modified_count)

    def _doc_to_entity(self, doc: Dict[str, Any]) -> Entity:
        from backend.models.EntityObjects.EAnimal import EAnimal
        from backend.models.EntityObjects.EFood import EFood
        from backend.models.EntityObjects.ENation import ENation
        from backend.models.EntityObjects.ENumber import ENumber
        from backend.models.EntityObjects.EPerson import EPerson
        from backend.models.EntityObjects.EPlace import EPlace
        from backend.models.EntityObjects.EPlant import EPlant
        from backend.models.EntityObjects.ESymbol import ESymbol
        from backend.models.EntityObjects.ETribeOfIsrael import ETribeOfIsrael

        doc = {k: v for k, v in doc.items() if k != "_id"}

        entity_type_value = doc.get(DBFields.ENTITY_TYPE)
        entity_type = EntityType(entity_type_value)

        entity_class_map = {
            EntityType.EPerson: EPerson,
            EntityType.EPlace: EPlace,
            EntityType.ENation: ENation,
            EntityType.ESymbol: ESymbol,
            EntityType.ETribeOfIsrael: ETribeOfIsrael,
            EntityType.ENumber: ENumber,
            EntityType.EAnimal: EAnimal,
            EntityType.EFood: EFood,
            EntityType.EPlant: EPlant,
        }

        entity_class = entity_class_map.get(entity_type, Entity)
        return entity_class.model_validate(doc)


