
from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import TimePeriod, RoleType, EntityType


class EPerson(Entity):
    entityType: EntityType = EntityType.EPerson
    timePeriod: TimePeriod
    isWoman: bool
    isNonJew: bool
    roles: list[RoleType] = []

    # transient:
    studiedFrom: list[str] = []
    siblingFrom: list[str] = []
    childOf: list[str] = []
    spouseOf: list[str] = []
    descendantOf: list[str] = []

    bornIn: list[str] = []
    diedId: list[str] = []
    visited: list[str] = []

    tribeOfIsrael: list[str] = []
    belongsToNation: list[str] = []

    allyOf: list[str] = []
    enemyOf: list[str] = []