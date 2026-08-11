# bs"d - lehagdil torah velahadir

from typing import List

from pydantic import Field

from backend.models_dto.EntitySelectOption import EntitySelectOption


class NumberSelectOption(EntitySelectOption):
    """
    Select option representing one distinct Number display value (e.g. "7").

    Many ENumber entities in the DB can share the same display_en_name (they
    differ by unit/context, e.g. "7 bulls" vs "7 years"), so options are
    grouped by display_en_name: the combobox shows a single chip per distinct
    number, and `entity_keys` carries every underlying entity key folded into
    that chip.
    """
    entity_keys: List[str] = Field(default_factory=list)

