from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import TimePeriod, RoleType


class EPerson(Entity):
    timePeriod: TimePeriod
    isWoman: bool
    isNonJew: bool
    role: RoleType