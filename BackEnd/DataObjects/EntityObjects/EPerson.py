from BackEnd.DataObjects.EntityObjects.Entity import Entity, TransientField
from BackEnd.DataObjects.Enums import TimePeriod, RoleType, EntityType
from typing import List


class EPerson(Entity):
    """
    Represents a Person entity - includes both individuals AND groups of people.
    Examples: Moses, David, Sarah, The 70 Elders, Children of Israel, The Sanhedrin.
    Also includes non-human beings like Angels and named animals.
    """
    # db fields
    entityType: EntityType = EntityType.EPerson
    timePeriod: TimePeriod
    isWoman: bool
    isNonJew: bool
    isGroup: bool = False  # True for groups like "the 70 elders", "children of Israel"
    roles: List[RoleType] = []

    # transient fields - Person/Group → Person/Group
    studiedFrom: List[str] = TransientField(default_factory=list)
    siblingFrom: List[str] = TransientField(default_factory=list)
    childOf: List[str] = TransientField(default_factory=list)
    spouseOf: List[str] = TransientField(default_factory=list)
    descendantOf: List[str] = TransientField(default_factory=list)
    allyOf: List[str] = TransientField(default_factory=list)
    enemyOf: List[str] = TransientField(default_factory=list)
    spokeWith: List[str] = TransientField(default_factory=list)

    # transient fields - Person/Group → Place
    bornIn: List[str] = TransientField(default_factory=list)
    diedIn: List[str] = TransientField(default_factory=list)
    visited: List[str] = TransientField(default_factory=list)

    # transient fields - Person/Group → TribeOfIsrael / Nation
    tribeOfIsrael: List[str] = TransientField(default_factory=list)
    belongsToNation: List[str] = TransientField(default_factory=list)

    # transient fields - Person/Group → {anything}
    prophesiedAbout: List[str] = TransientField(default_factory=list)

