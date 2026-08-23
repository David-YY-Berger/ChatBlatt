# bs"d - lehagdil torah velahadir

from typing import List, Optional

from pydantic import Field

from backend.models_db.Enums import RoleType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class PersonSelectOption(EntitySelectOption):
    """Person select option, extended with the metadata fields needed to
    power the entity-search combobox filters (faith, gender, group, role).
    isWoman/isNonJew/isGroup are None when unknown (not yet enriched) - they
    must NOT default to True/False, since that would misrepresent unknown
    data as a known man/woman, Jewish/non-Jewish, individual/group."""
    isWoman: Optional[bool] = None
    isNonJew: Optional[bool] = None
    isGroup: Optional[bool] = None
    roles: List[RoleType] = Field(default_factory=list)

