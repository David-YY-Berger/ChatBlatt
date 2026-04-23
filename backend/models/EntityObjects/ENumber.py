# bs"d - lehagdil torah velahadir

from typing import Optional
from backend.models.EntityObjects.Entity import Entity
from backend.models.Enums import EntityType, NumberCategory


class ENumber(Entity):
    entityType: EntityType = EntityType.ENumber
    numberCategory: Optional[NumberCategory] = None
    unit: Optional[str] = None                # Normalized singular noun — what the number counts/measures (e.g., "bull", "year", "silver")
    context: Optional[str] = None             # 1-6 word topic summary so the number is understandable out of context

