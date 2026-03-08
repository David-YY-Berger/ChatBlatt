from BackEnd.DataObjects.EntityObjects.Entity import Entity, TransientField
from BackEnd.DataObjects.Enums import TimePeriod, RoleType, EntityType
from typing import List


class EPerson(Entity):
    # db fields
    entityType: EntityType = EntityType.EPerson
    timePeriod: TimePeriod
    isWoman: bool
    isNonJew: bool
    roles: List[RoleType] = []

    # transient fields - Person → Person
    studiedFrom: List[str] = TransientField(default_factory=list)
    siblingFrom: List[str] = TransientField(default_factory=list)
    childOf: List[str] = TransientField(default_factory=list)
    spouseOf: List[str] = TransientField(default_factory=list)
    descendantOf: List[str] = TransientField(default_factory=list)
    allyOf: List[str] = TransientField(default_factory=list)
    enemyOf: List[str] = TransientField(default_factory=list)

    # transient fields - Person → Place
    bornIn: List[str] = TransientField(default_factory=list)
    diedIn: List[str] = TransientField(default_factory=list)
    visited: List[str] = TransientField(default_factory=list)

    # transient fields - Person → TribeOfIsrael / Nation
    tribeOfIsrael: List[str] = TransientField(default_factory=list)
    belongsToNation: List[str] = TransientField(default_factory=list)
