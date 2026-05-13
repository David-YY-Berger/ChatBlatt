# bs"d - lehagdil torah velahadir

"""
Entity Transient Field Populator.

Given an Entity and its relationships from the DB, populates the entity's
transient fields by resolving related entity keys to display names.

Design: Abstract base with per-entity-type implementations.
Each entity type defines a REL_FIELD_MAP that maps (RelType, direction) -> transient field name.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import RelType
from backend.models_db.Rel import Rel


# Direction constants: whether the entity is term1 or term2 in the relationship
AS_TERM1 = "term1"  # entity is the subject
AS_TERM2 = "term2"  # entity is the object (reverse relationship)


class BaseEntityPopulator(ABC):
    """
    Abstract base for populating transient fields on an Entity from DB rels.

    Subclasses define REL_FIELD_MAP: a dict mapping
        (RelType, direction) -> transient_field_name
    where direction is AS_TERM1 or AS_TERM2.

    Example for Person:
        (RelType.childOfFather, AS_TERM1) -> "childOfFather"
        means: if this person is term1 in a childOfFather rel, populate childOfFather field with term2's name.
    """

    @abstractmethod
    def get_rel_field_map(self) -> Dict[Tuple[RelType, str], str]:
        """
        Returns mapping of (RelType, direction) -> transient field name.
        direction is AS_TERM1 or AS_TERM2.
        """
        ...

    def populate(self, entity: Entity, rels: List[Rel], db: DBapiMongoDB) -> Entity:
        """
        Populate all transient fields on the entity from the given relationships.
        Resolves entity keys to display_en_name for readability.
        Returns the same entity object with transient fields filled in.
        """
        rel_field_map = self.get_rel_field_map()

        # Collect all referenced entity keys for batch resolution
        all_keys = set()
        for rel in rels:
            all_keys.add(rel.term1)
            all_keys.add(rel.term2)
        all_keys.discard(entity.key)

        # Batch-resolve keys to display names
        key_to_name = self._resolve_keys_to_names(all_keys, db)

        # Populate transient fields
        for rel in rels:
            if rel.term1 == entity.key:
                # Entity is term1 -> the "other" is term2
                field_name = rel_field_map.get((rel.rel_type, AS_TERM1))
                other_key = rel.term2
            elif rel.term2 == entity.key:
                # Entity is term2 -> the "other" is term1
                field_name = rel_field_map.get((rel.rel_type, AS_TERM2))
                other_key = rel.term1
            else:
                continue

            if field_name is None:
                continue

            other_name = key_to_name.get(other_key, other_key)

            field_value = getattr(entity, field_name, None)
            if isinstance(field_value, list):
                if other_name not in field_value:
                    field_value.append(other_name)

        return entity

    def _resolve_keys_to_names(self, keys: set, db: DBapiMongoDB) -> Dict[str, str]:
        """Batch-resolve entity keys to display_en_name."""
        if not keys:
            return {}
        entities = db.get_entities_by_keys(list(keys))
        return {e.key: e.display_en_name for e in entities}


class PersonPopulator(BaseEntityPopulator):
    """Populates transient fields for EPerson entities."""

    def get_rel_field_map(self) -> Dict[Tuple[RelType, str], str]:
        return {
            # Person/Group → Person/Group (entity is term1)
            (RelType.studiedFrom, AS_TERM1): "studiedFrom",
            (RelType.childOfFather, AS_TERM1): "childOfFather",
            (RelType.childOfMother, AS_TERM1): "childOfMother",
            (RelType.spouseOf, AS_TERM1): "spouseOf",
            (RelType.spouseOf, AS_TERM2): "spouseOf",  # symmetric
            (RelType.descendantOf, AS_TERM1): "descendantOf",
            (RelType.allyOf, AS_TERM1): "allyOf",
            (RelType.allyOf, AS_TERM2): "allyOf",  # symmetric
            (RelType.enemyOf, AS_TERM1): "enemyOf",
            (RelType.enemyOf, AS_TERM2): "enemyOf",  # symmetric
            (RelType.spokeWith, AS_TERM1): "spokeWith",
            (RelType.spokeWith, AS_TERM2): "spokeWith",  # symmetric
            (RelType.disagreedWith, AS_TERM1): "disagreedWith",
            (RelType.disagreedWith, AS_TERM2): "disagreedWith",  # symmetric

            # Person/Group → Place (entity is term1)
            (RelType.bornIn, AS_TERM1): "bornIn",
            (RelType.diedIn, AS_TERM1): "diedIn",
            (RelType.visited, AS_TERM1): "visited",
            (RelType.prayedAt, AS_TERM1): "prayedAt",
            (RelType.associatedWithPlace, AS_TERM1): "associatedWithPlace",

            # Person/Group → TribeOfIsrael / Nation
            (RelType.personToTribeOfIsrael, AS_TERM1): "tribeOfIsrael",
            (RelType.personBelongsToNation, AS_TERM1): "belongsToNation",

            # Person/Group → {anything}
            (RelType.prophesiedAbout, AS_TERM1): "prophesiedAbout",

            # {anything} → {anything}
            (RelType.comparedTo, AS_TERM1): "comparedTo",
            (RelType.comparedTo, AS_TERM2): "comparedTo",
            (RelType.contrastedWith, AS_TERM1): "contrastedWith",
            (RelType.contrastedWith, AS_TERM2): "contrastedWith",
        }


class PlacePopulator(BaseEntityPopulator):
    """Populates transient fields for EPlace entities. (Stub for future use.)"""

    def get_rel_field_map(self) -> Dict[Tuple[RelType, str], str]:
        return {
            # Place is term2 in person→place rels (reverse)
            (RelType.diedIn, AS_TERM2): "personsDiedIn",
            (RelType.bornIn, AS_TERM2): "personsBornIn",
            (RelType.visited, AS_TERM2): "personsVisited",
            (RelType.prayedAt, AS_TERM2): "personsPrayedAt",
            (RelType.associatedWithPlace, AS_TERM2): "personsAssociated",
            (RelType.symbolAssociatedWithPlace, AS_TERM2): "symbolsAssociated",
            (RelType.placeToNation, AS_TERM1): "inNation",
            (RelType.comparedTo, AS_TERM1): "comparedTo",
            (RelType.comparedTo, AS_TERM2): "comparedTo",
            (RelType.contrastedWith, AS_TERM1): "contrastedWith",
            (RelType.contrastedWith, AS_TERM2): "contrastedWith",
        }


class NationPopulator(BaseEntityPopulator):
    """Populates transient fields for ENation entities. (Stub for future use.)"""

    def get_rel_field_map(self) -> Dict[Tuple[RelType, str], str]:
        return {
            (RelType.personBelongsToNation, AS_TERM2): "personsBelongTo",
            (RelType.placeToNation, AS_TERM2): "placesIn",
            (RelType.enemyOf, AS_TERM1): "enemyOf",
            (RelType.enemyOf, AS_TERM2): "enemyOf",
            (RelType.allyOf, AS_TERM1): "allyOf",
            (RelType.allyOf, AS_TERM2): "allyOf",
            (RelType.comparedTo, AS_TERM1): "comparedTo",
            (RelType.comparedTo, AS_TERM2): "comparedTo",
            (RelType.contrastedWith, AS_TERM1): "contrastedWith",
            (RelType.contrastedWith, AS_TERM2): "contrastedWith",
        }


class TribeOfIsraelPopulator(BaseEntityPopulator):
    """Populates transient fields for ETribeOfIsrael entities. (Stub for future use.)"""

    def get_rel_field_map(self) -> Dict[Tuple[RelType, str], str]:
        return {
            (RelType.personToTribeOfIsrael, AS_TERM2): "membersOfTribeIsrael",
            (RelType.comparedTo, AS_TERM1): "comparedTo",
            (RelType.comparedTo, AS_TERM2): "comparedTo",
            (RelType.contrastedWith, AS_TERM1): "contrastedWith",
            (RelType.contrastedWith, AS_TERM2): "contrastedWith",
        }


# ========================= Registry =========================

from backend.models_db.Enums import EntityType

POPULATOR_REGISTRY: Dict[EntityType, BaseEntityPopulator] = {
    EntityType.EPerson: PersonPopulator(),
    EntityType.EPlace: PlacePopulator(),
    EntityType.ENation: NationPopulator(),
    EntityType.ETribeOfIsrael: TribeOfIsraelPopulator(),
}


def get_populator(entity_type: EntityType) -> Optional[BaseEntityPopulator]:
    """Get the populator for a given entity type."""
    return POPULATOR_REGISTRY.get(entity_type)

