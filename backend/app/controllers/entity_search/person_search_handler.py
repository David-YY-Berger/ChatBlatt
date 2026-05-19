# bs"d - lehagdil torah velahadir

"""
Person Search Handler.

Concrete implementation of BaseEntitySearchHandler for Person entities.
"""

from __future__ import annotations

from typing import List, Tuple

from backend.app.controllers.entity_search.entity_search_controller import BaseEntitySearchHandler
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType, RelType
from backend.models_dto.EntitySelectOption import EntitySelectOption


class PersonSearchHandler(BaseEntitySearchHandler):
    """Entity search handler for Person entities."""

    def get_entity_type(self) -> EntityType:
        return EntityType.EPerson

    def get_select_options(self) -> List[EntitySelectOption]:
        return self.db.getPersonSelectOptions()

    def get_transient_field_labels(self) -> List[Tuple[str, str]]:
        """
        Ordered list of (field_name, translation_key) for Person transient fields.
        These are displayed as scrollable lists in the UI.

        Field names use RelType.value where the EPerson attribute name matches the
        RelType member value.  The two exceptions are 'tribeOfIsrael' and
        'belongsToNation': these are the EPerson attribute names, which differ from
        their RelType counterparts (personToTribeOfIsrael / personBelongsToNation).
        """
        R = RelType  # local alias for brevity
        return [
            # Person → Person
            (R.childOfFather.value,      f"entity_fields.{R.childOfFather.value}"),
            (R.childOfMother.value,      f"entity_fields.{R.childOfMother.value}"),
            (R.spouseOf.value,           f"entity_fields.{R.spouseOf.value}"),
            (R.descendantOf.value,       f"entity_fields.{R.descendantOf.value}"),
            (R.studiedFrom.value,        f"entity_fields.{R.studiedFrom.value}"),
            (R.spokeWith.value,          f"entity_fields.{R.spokeWith.value}"),
            (R.disagreedWith.value,      f"entity_fields.{R.disagreedWith.value}"),
            (R.allyOf.value,             f"entity_fields.{R.allyOf.value}"),
            (R.enemyOf.value,            f"entity_fields.{R.enemyOf.value}"),
            # Person → Place
            (R.bornIn.value,             f"entity_fields.{R.bornIn.value}"),
            (R.diedIn.value,             f"entity_fields.{R.diedIn.value}"),
            (R.visited.value,            f"entity_fields.{R.visited.value}"),
            (R.prayedAt.value,           f"entity_fields.{R.prayedAt.value}"),
            (R.associatedWithPlace.value, f"entity_fields.{R.associatedWithPlace.value}"),
            # Person → TribeOfIsrael / Nation
            # EPerson uses 'tribeOfIsrael' / 'belongsToNation' as attribute names,
            # which differ from RelType.personToTribeOfIsrael / personBelongsToNation.
            ("tribeOfIsrael",   "entity_fields.tribeOfIsrael"),
            ("belongsToNation", "entity_fields.belongsToNation"),
            # Person → {anything}
            (R.prophesiedAbout.value,    f"entity_fields.{R.prophesiedAbout.value}"),
            # General
            (R.comparedTo.value,         f"entity_fields.{R.comparedTo.value}"),
            (R.contrastedWith.value,     f"entity_fields.{R.contrastedWith.value}"),
        ]

    def get_db_field_display(self, entity: Entity) -> List[Tuple[str, str]]:
        """Display the Person-specific DB fields."""
        from backend.models_db.EntityObjects.EPerson import EPerson
        if not isinstance(entity, EPerson):
            return []

        fields = [
            ("entity_fields.timePeriod", entity.timePeriod.value if entity.timePeriod else ""),
            ("entity_fields.isWoman", "✓" if entity.isWoman else "✗"),
            ("entity_fields.isNonJew", "✓" if entity.isNonJew else "✗"),
            ("entity_fields.isGroup", "✓" if entity.isGroup else "✗"),
        ]
        if entity.roles:
            fields.append(("entity_fields.roles", ", ".join(r.value for r in entity.roles)))
        return fields

