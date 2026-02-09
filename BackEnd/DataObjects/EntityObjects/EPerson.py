
from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import TimePeriod, RoleType, EntityType


class EPerson(Entity):
    entityType: EntityType = EntityType.EPerson
    timePeriod: TimePeriod
    isWoman: bool
    isNonJew: bool
    role: RoleType