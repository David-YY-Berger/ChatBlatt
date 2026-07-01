import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType

if TYPE_CHECKING:
    from backend.models_db.EntityObjects.EntityIdentity import PersonFamilyContext


class EntityMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    # ========================= Primary insert method =========================

    def try_insert_entity(self, entity: Entity, person_family_names: Optional["PersonFamilyContext"] = None) -> str:
        """
        Inserts an Entity if it does not already exist.
        For Person entities: queries all persons with the same name from the DB,
        then checks their family relationships (from the rels collection) to
        determine if any existing person matches the one being inserted.
        For other entity types: uses name + type equality.
        Returns the key (str of ObjectId) whether newly inserted or already existing.
        """
        existing_key = self._find_existing_entity_key(entity, person_family_names)
        if existing_key:
            return existing_key

        data = entity.to_db_dict()
        data[DBFields.ENTITY_TYPE] = entity.entityType.value
        # Remove empty key so Mongo generates _id
        data.pop(DBFields.KEY, None)

        result = self.get_collection(CollectionObjs.ENTITIES).insert_one(data)
        generated_key = str(result.inserted_id)

        # Persist the key back into the document
        self.get_collection(CollectionObjs.ENTITIES).update_one(
            {"_id": result.inserted_id},
            {DBOperators.SET: {DBFields.KEY: generated_key}},
        )
        return generated_key

    def _find_existing_entity_key(self, entity: Entity, person_family_names: Optional["PersonFamilyContext"] = None) -> Optional[str]:
        """
        Check if an entity already exists in the DB.
        For Person entities with family context: finds all persons with the same name,
        then compares their DB relationships against the provided family context.
        For other types: simple name + type match.
        Returns its key if found, else None.
        """
        from backend.models_db.Enums import EntityType

        if entity.entityType == EntityType.EPerson and person_family_names is not None:
            return self._find_existing_person_by_family(entity, person_family_names)

        # Default: simple name + type query
        query = entity.build_existence_query()
        doc = self.get_collection(CollectionObjs.ENTITIES).find_one(query)
        if doc is None:
            return None
        return doc.get(DBFields.KEY) or str(doc["_id"])

    def _find_existing_person_by_family(self, entity: Entity, new_family: "PersonFamilyContext") -> Optional[str]:
        """
        Find an existing Person in the DB that matches the given entity by name
        AND family relationships.

        Logic:
        1. Get all persons with same display_en_name (case-insensitive).
        2. For each, query the rels collection for childOfFather/childOfMother/spouseOf.
        3. If the new person has no family context, return the first name match.
        4. If a DB person shares a father, mother, or spouse -> same person.
        5. If no DB person matches family context -> not found (will be inserted as new).
        """
        from backend.models_db.EntityObjects.EntityIdentity import PersonFamilyContext

        # Find all persons with same name
        query = entity.build_existence_query()
        docs = list(self.get_collection(CollectionObjs.ENTITIES).find(query))
        if not docs:
            return None

        # If new person has no family info at all, any name match is sufficient
        has_family_info = bool(new_family.fathers or new_family.mothers or new_family.spouses)
        if not has_family_info:
            doc = docs[0]
            return doc.get(DBFields.KEY) or str(doc["_id"])

        # Check each existing person's family rels from the DB
        for doc in docs:
            existing_key = doc.get(DBFields.KEY) or str(doc["_id"])
            db_family = self.get_family_context_for_entity(existing_key)

            # DB person also has no family info -> treat as same (ambiguous)
            if not db_family.fathers and not db_family.mothers and not db_family.spouses:
                return existing_key

            # Same father
            if new_family.fathers and db_family.fathers:
                if new_family.fathers & db_family.fathers:
                    return existing_key

            # Same mother
            if new_family.mothers and db_family.mothers:
                if new_family.mothers & db_family.mothers:
                    return existing_key

            # Same spouse
            if new_family.spouses and db_family.spouses:
                if new_family.spouses & db_family.spouses:
                    return existing_key

            # Cross-check: new person's father is spouse of DB person's mother (or vice versa)
            for father in new_family.fathers:
                for mother in db_family.mothers:
                    if self._are_spouses_in_db(father, mother):
                        return existing_key
            for father in db_family.fathers:
                for mother in new_family.mothers:
                    if self._are_spouses_in_db(father, mother):
                        return existing_key

        # No match found
        return None

    def _are_spouses_in_db(self, name1: str, name2: str) -> bool:
        """
        Check if two people (by lowercased name) are spouses according to DB rels.
        Finds entity keys for both names, then checks for a spouseOf rel between them.
        """
        from backend.models_db.Enums import RelType

        # Find entities by name
        regex1 = {DBOperators.REGEX: f"^{name1}$", DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE}
        doc1 = self.get_collection(CollectionObjs.ENTITIES).find_one({DBFields.DISPLAY_EN_NAME: regex1})
        if not doc1:
            return False
        key1 = doc1.get(DBFields.KEY) or str(doc1["_id"])

        regex2 = {DBOperators.REGEX: f"^{name2}$", DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE}
        doc2 = self.get_collection(CollectionObjs.ENTITIES).find_one({DBFields.DISPLAY_EN_NAME: regex2})
        if not doc2:
            return False
        key2 = doc2.get(DBFields.KEY) or str(doc2["_id"])

        # Check spouseOf in either direction
        spouse_rel = self.get_collection(CollectionObjs.RELATIONS).find_one({
            DBFields.REL_TYPE: RelType.spouseOf.value,
            DBOperators.OR: [
                {DBFields.TERM1: key1, DBFields.TERM2: key2},
                {DBFields.TERM1: key2, DBFields.TERM2: key1},
            ]
        })
        return spouse_rel is not None

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
            DBFields.DISPLAY_EN_NAME: {
                DBOperators.REGEX: f"^{re.escape(value)}$",
                DBOperators.OPTIONS: DBOperators.CASE_INSENSITIVE,
            },
        }
        docs = self.get_collection(CollectionObjs.ENTITIES).find(query)
        return [self._doc_to_entity(doc) for doc in docs]

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


