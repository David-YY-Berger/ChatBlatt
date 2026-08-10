# bs"d - lehagdil torah velahadir

from typing import List

from pydantic import Field

from backend.models_db.Enums import RoleType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class PersonSelectOption(EntitySelectOption):
    """Person select option, extended with the metadata fields needed to
    power the entity-search combobox filters (faith, gender, group, role)."""
    isWoman: bool = False
    isNonJew: bool = False
    isGroup: bool = False
    roles: List[RoleType] = Field(default_factory=list)

