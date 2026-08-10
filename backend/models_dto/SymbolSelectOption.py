# bs"d - lehagdil torah velahadir

from typing import Optional

from backend.models_db.Enums import SymbolType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class SymbolSelectOption(EntitySelectOption):
    """Symbol select option, extended with symbolType for combobox filtering."""
    symbolType: Optional[SymbolType] = None

