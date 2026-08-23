# bs"d - lehagdil torah velahadir

from typing import Callable, Dict, List, Optional

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields
from backend.models_db.Enums import EntityType
from backend.models_dto.AnimalSelectOption import AnimalSelectOption
from backend.models_dto.FoodSelectOption import FoodSelectOption
from backend.models_dto.NationSelectOption import NationSelectOption
from backend.models_dto.NumberSelectOption import NumberSelectOption
from backend.models_dto.PersonSelectOption import PersonSelectOption
from backend.models_dto.PlaceSelectOption import PlaceSelectOption
from backend.models_dto.PlantSelectOption import PlantSelectOption
from backend.models_dto.SymbolSelectOption import SymbolSelectOption
from backend.models_dto.TribeOfIsraelSelectOption import TribeOfIsraelSelectOption


class SelectOptionMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    # ========================= Select Option queries =========================

    def _docs_to_select_options(self, docs, option_class, extra_fields: Optional[Callable[[dict], Dict]] = None):
        """Convert a list of mongo documents to the given SelectOption class.

        `extra_fields`, if given, is a callable(doc) -> dict of extra kwargs
        used to populate type-specific metadata fields (e.g. roles, placeType)
        that power the entity-search combobox filters.
        """
        results = []
        for doc in docs:
            kwargs = dict(
                key=doc.get(DBFields.KEY, str(doc.get("_id", ""))),
                display_en_name=doc.get(DBFields.DISPLAY_EN_NAME, ""),
                display_heb_name=doc.get(DBFields.DISPLAY_HEB_NAME, ""),
                all_en_names=doc.get(DBFields.ALL_EN_NAMES, []),
                all_heb_names=doc.get(DBFields.ALL_HEB_NAMES, []),
            )
            if extra_fields is not None:
                kwargs.update(extra_fields(doc))
            results.append(option_class(**kwargs))
        return results

    @staticmethod
    def _person_extra_fields(doc: dict) -> dict:
        # isWoman/isNonJew/isGroup default to None (unknown) rather than
        # False when absent from the doc - a missing/unenriched value must
        # not be mistaken for a known "man"/"Jewish"/"individual".
        return {
            "isWoman": doc.get("isWoman"),
            "isNonJew": doc.get("isNonJew"),
            "isGroup": doc.get("isGroup"),
            "roles": doc.get("roles", []),
        }

    @staticmethod
    def _place_extra_fields(doc: dict) -> dict:
        return {"placeType": doc.get("placeType")}

    @staticmethod
    def _symbol_extra_fields(doc: dict) -> dict:
        return {"symbolType": doc.get("symbolType")}

    def getPersonSelectOptions(self) -> List[PersonSelectOption]:
        """Query all Person entities and return as PersonSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.EPerson.value}
        )
        return self._docs_to_select_options(docs, PersonSelectOption, self._person_extra_fields)

    def getPlaceSelectOptions(self) -> List[PlaceSelectOption]:
        """Query all Place entities and return as PlaceSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.EPlace.value}
        )
        return self._docs_to_select_options(docs, PlaceSelectOption, self._place_extra_fields)

    def getSymbolSelectOptions(self) -> List[SymbolSelectOption]:
        """Query all Symbol entities and return as SymbolSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.ESymbol.value}
        )
        return self._docs_to_select_options(docs, SymbolSelectOption, self._symbol_extra_fields)

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

    def getNumberSelectOptions(self) -> List[NumberSelectOption]:
        """Query all Number entities and collapse them into one select option
        per distinct display_en_name (e.g. many "7" entities — "7 bulls",
        "7 years", etc. — become a single "7" chip). `entity_keys` on each
        returned option lists every underlying ENumber entity key sharing
        that display name. Hebrew names are intentionally omitted so numbers
        show only their English display name in the combobox.
        """
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.ENumber.value}
        )
        grouped_keys: Dict[str, List[str]] = {}
        for doc in docs:
            display_name = doc.get(DBFields.DISPLAY_EN_NAME, "")
            entity_key = doc.get(DBFields.KEY, str(doc.get("_id", "")))
            grouped_keys.setdefault(display_name, []).append(entity_key)

        def _sort_key(name: str):
            try:
                return (0, float(name))
            except (TypeError, ValueError):
                return (1, name)

        return [
            NumberSelectOption(
                key=keys[0],
                display_en_name=display_name,
                entity_keys=keys,
            )
            for display_name, keys in sorted(grouped_keys.items(), key=lambda item: _sort_key(item[0]))
        ]

    def getAnimalSelectOptions(self) -> List[AnimalSelectOption]:
        """Query all Animal entities and return as AnimalSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.EAnimal.value}
        )
        return self._docs_to_select_options(docs, AnimalSelectOption)

    def getFoodSelectOptions(self) -> List[FoodSelectOption]:
        """Query all Food entities and return as FoodSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.EFood.value}
        )
        return self._docs_to_select_options(docs, FoodSelectOption)

    def getPlantSelectOptions(self) -> List[PlantSelectOption]:
        """Query all Plant entities and return as PlantSelectOption list."""
        docs = self.get_collection(CollectionObjs.ENTITIES).find(
            {DBFields.ENTITY_TYPE: EntityType.EPlant.value}
        )
        return self._docs_to_select_options(docs, PlantSelectOption)

