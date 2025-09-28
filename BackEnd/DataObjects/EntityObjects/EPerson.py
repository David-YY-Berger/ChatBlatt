from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Enums import TimePeriod


class EPerson(Entity):
    timePeriod: TimePeriod
    isWoman: bool
    isNonJew: bool