# bs"d - lehagdil torah velahadir

from typing import Optional

from backend.models_db.Enums import PlaceType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class PlaceSelectOption(EntitySelectOption):
    """Place select option, extended with placeType for combobox filtering."""
    placeType: Optional[PlaceType] = None

