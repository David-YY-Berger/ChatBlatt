# bs"d - lehagdil torah velahadir

from __future__ import annotations

from backend.models_db.EntityObjects.Entity import Entity, TransientField
from backend.models_db.Enums import TimePeriod, RoleType, EntityType
from typing import Any, ClassVar, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models_db.EntityObjects.EntityIdentity import EntityIdentityContext


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
    isWoman: bool = False
    isNonJew: bool = False
    isGroup: bool = False  # True for groups like "the 70 elders", "children of Israel"
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

    # ========================= Identity / Equality =========================

    def get_identity_tuple(self, context: Optional["EntityIdentityContext"] = None) -> tuple:
        """
        Person equality:
          - Same name AND same father, OR
          - Same name AND same mother, OR
          - Same name AND father(1) is spouse of mother(2) or vice versa, OR
          - Same name (fallback when no family context exists)

        Returns a tuple that encodes the identity. When family context is available,
        the tuple includes a frozenset of parent names so that persons with different
        parents are treated as distinct even if they share a name.
        """
        name_lower = self.display_en_name.lower()

        if context is None:
            return (name_lower, self.entityType)

        person_ctx = context.get_person_context(self.display_en_name)
        if person_ctx is None or (not person_ctx.fathers and not person_ctx.mothers):
            # No family info — fall back to name-only
            return (name_lower, self.entityType)

        # Build a canonical family fingerprint:
        # Include fathers and mothers so that two people with the same name
        # but different parents get different identity tuples.
        family_key = (
            frozenset(person_ctx.fathers),
            frozenset(person_ctx.mothers),
        )
        return (name_lower, self.entityType, family_key)

    def build_existence_query(self, context: Optional["EntityIdentityContext"] = None) -> Dict[str, Any]:
        """
        Person existence query:
        Checks in DB for a person with the same name who ALSO shares at least one
        parent (via childOfFather / childOfMother relationships).
        Falls back to name-only if no family context.
        """
        from backend.db.DBConstants import DBFields

        base_query = {
            DBFields.DISPLAY_EN_NAME: self.display_en_name,  # already lowercase
            DBFields.ENTITY_TYPE: self.entityType.value,
        }

        # For DB-level check we return the base query.
        # The family-context check is done in-memory by get_identity_tuple
        # (since relationship data is in a separate collection and the full
        #  cross-collection check is handled by the populator's entity_key_map).
        return base_query

    def is_same_person(self, other_name: str, context: Optional["EntityIdentityContext"] = None) -> bool:
        """
        Determine whether `other_name` refers to the same person as `self`,
        using the full Person equality rules:

        1. display_en_name == other AND same father
        2. display_en_name == other AND same mother
        3. display_en_name == other AND father(self) is spouse of mother(other)
        4. display_en_name == other AND father(other) is spouse of mother(self)
        """
        if self.display_en_name.lower() != other_name.lower():
            return False

        if context is None:
            return True  # same name, no context to distinguish

        self_ctx = context.get_person_context(self.display_en_name)
        other_ctx = context.get_person_context(other_name)

        # If neither has family info, treat same name as same person
        if not self_ctx and not other_ctx:
            return True

        # If only one has family info, they might still be the same (ambiguous)
        if not self_ctx or not other_ctx:
            return True

        # Rule 1: same father
        if self_ctx.fathers & other_ctx.fathers:
            return True

        # Rule 2: same mother
        if self_ctx.mothers & other_ctx.mothers:
            return True

        # Rule 3: father(self) is spouse of mother(other)
        for father in self_ctx.fathers:
            for mother in other_ctx.mothers:
                if context.are_spouses(father, mother):
                    return True

        # Rule 4: father(other) is spouse of mother(self)
        for father in other_ctx.fathers:
            for mother in self_ctx.mothers:
                if context.are_spouses(father, mother):
                    return True

        # Different family — different person despite same name
        return False

