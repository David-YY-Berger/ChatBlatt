# bs"d - lehagdil torah velahadir

from __future__ import annotations

from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import TimePeriod, RoleType, EntityType
from typing import Any, ClassVar, Dict, List, Optional


class EPerson(Entity):
    """
    Represents a Person entity - includes both individuals AND groups of people.
    Examples: Moses, David, Sarah, The 70 Elders, Children of Israel, The Sanhedrin.
    Also includes non-human beings like Angels.
    Note: Talking animals (e.g., Balaam's Donkey) are now in the Animal category.
    """

    # Ordered tuple of transient field names used for UI display.
    # This is the single source of truth for which EPerson attributes are shown
    # and in what order (used by PersonSearchHandler.get_transient_field_labels).
    TRANSIENT_DISPLAY_FIELDS: ClassVar[tuple] = (
        # Person → Person
        "childOfFather",
        "childOfMother",
        "children",
        "siblings",
        "spouseOf",
        "descendantOf",
        "studiedFrom",
        "spokeWith",
        "disagreedWith",
        "allyOf",
        "enemyOf",
        # Person → Place
        "bornIn",
        "diedIn",
        "visited",
        "prayedAt",
        "associatedWithPlace",
        # Person → TribeOfIsrael / Nation
        "tribeOfIsrael",
        "belongsToNation",
        # Person → {anything}
        "prophesiedAbout",
        # General
        "comparedTo",
        "contrastedWith",
    )

    # db fields
    entityType: EntityType = EntityType.EPerson
    timePeriod: Optional[TimePeriod] = None
    isWoman: Optional[bool] = None
    isNonJew: Optional[bool] = None
    isGroup: Optional[bool] = None  # True for groups like "the 70 elders", "children of Israel"
    roles: List[RoleType] = []

    # transient fields - Person/Group → Person/Group
    studiedFrom: List[str] = TransientField(default_factory=list)
    childOfFather: List[str] = TransientField(default_factory=list)
    childOfMother: List[str] = TransientField(default_factory=list)
    children: List[str] = TransientField(default_factory=list)   # people whose father/mother is this person
    siblings: List[str] = TransientField(default_factory=list)   # people sharing the same father or mother
    spouseOf: List[str] = TransientField(default_factory=list)
    descendantOf: List[str] = TransientField(default_factory=list)
    allyOf: List[str] = TransientField(default_factory=list)
    enemyOf: List[str] = TransientField(default_factory=list)
    spokeWith: List[str] = TransientField(default_factory=list)
    disagreedWith: List[str] = TransientField(default_factory=list)

    # transient fields - Person/Group → Place
    bornIn: List[str] = TransientField(default_factory=list)
    diedIn: List[str] = TransientField(default_factory=list)
    visited: List[str] = TransientField(default_factory=list)
    prayedAt: List[str] = TransientField(default_factory=list)
    associatedWithPlace: List[str] = TransientField(default_factory=list)  # fallback

    # transient fields - Person/Group → TribeOfIsrael / Nation
    tribeOfIsrael: List[str] = TransientField(default_factory=list)
    belongsToNation: List[str] = TransientField(default_factory=list)

    # transient fields - Person/Group → {anything}
    prophesiedAbout: List[str] = TransientField(default_factory=list)

    def has_metadata(self) -> bool:
        return (
            super().has_metadata()
            and self.timePeriod is not None
            and self.isWoman is not None
            and self.isNonJew is not None
            and self.isGroup is not None
            and self.roles is not None
        )

    # ========================= Identity / Equality =========================

    def get_identity_tuple(self) -> tuple:
        """
        Person equality (per this tuple alone): same display_en_name + same entityType.

        NOTE: This is only a name-based dedup key used for in-batch bookkeeping
        (e.g. entity_key_map in the populator). It intentionally does NOT
        disambiguate two different people who share a display_en_name — that
        disambiguation happens at DB-insert time via PersonFamilyContext
        (see EntityMongoMixin._find_existing_person_by_family), which compares
        father/mother/spouse relationships pulled from the DB.
        """
        return (self.display_en_name.lower(), self.entityType)

    def build_existence_query(self) -> Dict[str, Any]:
        """
        Person existence query: base lookup by name + type.
        Used to fetch all same-named candidates from the DB; the actual
        family-based disambiguation among candidates is done separately
        (see EntityMongoMixin._find_existing_person_by_family).
        """
        from backend.db.DBConstants import DBFields

        return {
            DBFields.DISPLAY_EN_NAME: self.display_en_name,  # already lowercase
            DBFields.ENTITY_TYPE: self.entityType.value,
        }

