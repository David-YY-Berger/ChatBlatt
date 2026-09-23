from typing import Any, Dict, List, Optional, Tuple

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType


class EntityMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    # ========================= Primary insert method =========================

    def try_insert_entity(self, entity: Entity) -> str:
        """
        Inserts an Entity unless an 'equal' one already exists (by default same
        display_en_name + entityType - see Entity.build_existence_query).
        Returns the key (str of ObjectId) whether newly inserted or already existing.

        NOTE: Person mentions extracted from sources should NOT come through here -
        several different people can share a display_en_name, so the populator
        resolves them via PersonDisambiguator and calls insert_entity for new ones.
        """
        existing_key = self._find_existing_entity_key(entity)
        if existing_key:
            return existing_key
        return self.insert_entity(entity)

    def _find_existing_entity_key(self, entity: Entity) -> Optional[str]:
        """Returns the key of an existing entity 'equal' to this one (see Entity.build_existence_query), else None."""
        query = entity.build_existence_query()
        doc = self.get_collection(CollectionObjs.ENTITIES).find_one(query)
        if doc is None:
            return None
        return doc.get(DBFields.KEY) or str(doc["_id"])

    def insert_entity(self, entity: Entity) -> str:
        """
        Plain insert (no dedup check). Satisfies the EntityInterfaceMixin contract.
        Inserts the entity and stores the MongoDB-generated key back into the document.
        """
        data = entity.to_db_dict()
        data[DBFields.ENTITY_TYPE] = entity.entityType.value
        data.pop(DBFields.KEY, None)

        result = self.get_collection(CollectionObjs.ENTITIES).insert_one(data)
        generated_key = str(result.inserted_id)

        self.get_collection(CollectionObjs.ENTITIES).update_one(
            {"_id": result.inserted_id},
            {DBOperators.SET: {DBFields.KEY: generated_key}},
        )
        return generated_key

    # ========================= Query methods =========================

    def is_entity_exists(self, key: str) -> bool:
        return self.get_collection(CollectionObjs.ENTITIES).find_one({DBFields.KEY: key}) is not None

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

    def drop_all_entities(self) -> int:
        """Delete all entity documents from the entities collection. Returns deleted count."""
        result = self.get_collection(CollectionObjs.ENTITIES).delete_many({})
        return result.deleted_count

    def get_enumbers_by_value(self, value: str) -> List["ENumber"]:
        """
        Return all ENumber entities whose display_en_name exactly matches
        the given value (case-insensitive). Used by the number-search feature.
        """
        from backend.models_db.EntityObjects.ENumber import ENumber

        query = {
            DBFields.ENTITY_TYPE: EntityType.ENumber.value,
            DBFields.DISPLAY_EN_NAME: value.lower(),
        }
        docs = self.get_collection(CollectionObjs.ENTITIES).find(query)
        return [self._doc_to_entity(doc) for doc in docs]

    def get_entities_by_display_en_name(self, display_en_name: str, entity_type: Optional[EntityType] = None) -> List[Entity]:
        """
        Return all entities whose display_en_name exactly matches the given name
        (case-insensitive; display_en_name is always stored lowercase). Optionally
        restrict to a specific entity_type. Used to find candidate duplicate
        entities that share a display name (e.g. for merge/dedup workflows).
        """
        query: Dict[str, Any] = {DBFields.DISPLAY_EN_NAME: display_en_name.strip().lower()}
        if entity_type is not None:
            query[DBFields.ENTITY_TYPE] = entity_type.value
        docs = self.get_collection(CollectionObjs.ENTITIES).find(query)
        return [self._doc_to_entity(doc) for doc in docs]

    def delete_entity_by_key(self, key: str) -> int:
        """Delete a single entity document by its key. Returns the number of deleted documents (0 or 1)."""
        result = self.get_collection(CollectionObjs.ENTITIES).delete_one({DBFields.KEY: key})
        return result.deleted_count

    def _doc_to_entity(self, doc: Dict[str, Any]) -> Entity:
        from backend.models_db.EntityObjects.EAnimal import EAnimal
        from backend.models_db.EntityObjects.EFood import EFood
        from backend.models_db.EntityObjects.ENation import ENation
        from backend.models_db.EntityObjects.ENumber import ENumber
        from backend.models_db.EntityObjects.EPerson import EPerson
        from backend.models_db.EntityObjects.EPlace import EPlace
        from backend.models_db.EntityObjects.EPlant import EPlant
        from backend.models_db.EntityObjects.ESymbol import ESymbol
        from backend.models_db.EntityObjects.ETribeOfIsrael import ETribeOfIsrael

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


