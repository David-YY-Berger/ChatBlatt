# bs"d - lehagdil torah velahadir

from typing import List

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields
from backend.models_db.Enums import EntityType
from backend.models_dto.NationSelectOption import NationSelectOption
from backend.models_dto.PersonSelectOption import PersonSelectOption
from backend.models_dto.PlaceSelectOption import PlaceSelectOption
from backend.models_dto.TribeOfIsraelSelectOption import TribeOfIsraelSelectOption


class SelectOptionMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    # ========================= Select Option queries =========================

    def _docs_to_select_options(self, docs, option_class):
        """Convert a list of mongo documents to the given SelectOption class."""
        results = []
        for doc in docs:
            results.append(option_class(
                key=doc.get(DBFields.KEY, str(doc.get("_id", ""))),
                display_en_name=doc.get(DBFields.DISPLAY_EN_NAME, ""),
                display_heb_name=doc.get(DBFields.DISPLAY_HEB_NAME, ""),
                all_en_names=doc.get(DBFields.ALL_EN_NAMES, []),
                all_heb_names=doc.get(DBFields.ALL_HEB_NAMES, []),
            ))
        return results

    def getPersonSelectOptions(self) -> List[PersonSelectOption]:
        """Query all Person entities and return as PersonSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.EPerson.value}
        )
        return self._docs_to_select_options(docs, PersonSelectOption)

    def getPlaceSelectOptions(self) -> List[PlaceSelectOption]:
        """Query all Place entities and return as PlaceSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.EPlace.value}
        )
        return self._docs_to_select_options(docs, PlaceSelectOption)

    def getNationSelectOptions(self) -> List[NationSelectOption]:
        """Query all Nation entities and return as NationSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.ENation.value}
        )
        return self._docs_to_select_options(docs, NationSelectOption)

    def getTribeOfIsraelSelectOptions(self) -> List[TribeOfIsraelSelectOption]:
        """Query all TribeOfIsrael entities and return as TribeOfIsraelSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.ETribeOfIsrael.value}
        )
        return self._docs_to_select_options(docs, TribeOfIsraelSelectOption)

