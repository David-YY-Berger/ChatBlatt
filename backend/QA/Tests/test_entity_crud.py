# bs"d
"""
CRUD tests for every Entity subclass via the Mongo mixins (FakeCollection-backed).
Each entity type gets: Create, Read, Update, Delete, bulk insert, upsert, search.
"""
import logging
import unittest

from backend.QA.Tests.conftest import FakeDBapi
from backend.models.Enums import (
    TimePeriod, RoleType, PlaceType, SymbolType, NumberCategory,
)
from backend.models.EntityObjects.EPerson import EPerson
from backend.models.EntityObjects.EPlace import EPlace
from backend.models.EntityObjects.EAnimal import EAnimal
from backend.models.EntityObjects.EFood import EFood
from backend.models.EntityObjects.ENation import ENation
from backend.models.EntityObjects.ENumber import ENumber
from backend.models.EntityObjects.EPlant import EPlant
from backend.models.EntityObjects.ESymbol import ESymbol
from backend.models.EntityObjects.ETribeOfIsrael import ETribeOfIsrael

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

_COMMON = dict(all_en_names=["Test"], all_heb_names=["טסט"], alias_keys=[])


class EntityCRUDBase(unittest.TestCase):
    entity = None
    entity_updated = None

    def setUp(self):
        if self.__class__ is EntityCRUDBase:
            self.skipTest("Base class – skipped")
        self.db = FakeDBapi.create()

    def test_insert_entity(self):
        eid = self.db.insert_entity(self.entity)
        self.assertTrue(eid, f"INSERT failed for {self.entity.__class__.__name__} – returned falsy id")
        log.info("INSERT OK  %s  key=%s", self.entity.__class__.__name__, self.entity.key)

    def test_read_entity_by_key(self):
        self.db.insert_entity(self.entity)
        result = self.db.get_entity_by_key(self.entity.key)
        self.assertIsNotNone(result, f"READ by key failed for {self.entity.__class__.__name__} – got None")
        self.assertEqual(result.key, self.entity.key,
                         f"READ key mismatch: expected {self.entity.key}, got {result.key}")
        self.assertIsInstance(result, self.entity.__class__,
                              f"READ type mismatch: expected {self.entity.__class__.__name__}, got {type(result).__name__}")
        log.info("READ OK    %s  key=%s", self.entity.__class__.__name__, self.entity.key)

    def test_read_entities_by_type(self):
        self.db.insert_entity(self.entity)
        results = self.db.get_entities_by_type(self.entity.entityType)
        self.assertGreaterEqual(len(results), 1,
                                f"READ by type returned 0 for {self.entity.entityType}")
        log.info("READ-TYPE  %s  count=%d", self.entity.entityType, len(results))

    def test_entity_exists(self):
        self.assertFalse(self.db.is_entity_exists(self.entity.key),
                         f"EXISTS True before insert for {self.entity.key}")
        self.db.insert_entity(self.entity)
        self.assertTrue(self.db.is_entity_exists(self.entity.key),
                        f"EXISTS False after insert for {self.entity.key}")

    def test_update_entity(self):
        self.db.insert_entity(self.entity)
        modified = self.db.update_entity(self.entity_updated)
        self.assertEqual(modified, 1, f"UPDATE modified_count!=1 for {self.entity.__class__.__name__}")
        refreshed = self.db.get_entity_by_key(self.entity.key)
        self.assertEqual(refreshed.display_en_name, self.entity_updated.display_en_name,
                         f"UPDATE field not persisted for {self.entity.__class__.__name__}")
        log.info("UPDATE OK  %s", self.entity.__class__.__name__)

    def test_delete_entity(self):
        from backend.db.Collections import CollectionObjs
        self.db.insert_entity(self.entity)
        deleted = self.db.get_collection(CollectionObjs.ENTITIES).delete_many({"key": self.entity.key}).deleted_count
        self.assertEqual(deleted, 1, f"DELETE count!=1 for {self.entity.__class__.__name__}")
        self.assertIsNone(self.db.get_entity_by_key(self.entity.key),
                          f"DELETE entity still readable for {self.entity.key}")
        log.info("DELETE OK  %s", self.entity.__class__.__name__)

    def test_insert_entities_bulk(self):
        count = self.db.insert_entities_bulk([self.entity])
        self.assertEqual(count, 1, f"BULK INSERT returned {count} for {self.entity.__class__.__name__}")

    def test_search_entities_by_name(self):
        self.db.insert_entity(self.entity)
        results = self.db.search_entities_by_name(self.entity.display_en_name[:4])
        self.assertGreaterEqual(len(results), 1,
                                f"SEARCH found 0 for '{self.entity.display_en_name[:4]}'")

    def test_upsert_bulk_insert_path(self):
        upserted, modified = self.db.upsert_entities_bulk([self.entity])
        self.assertEqual(upserted, 1, f"UPSERT-BULK upserted!=1 for {self.entity.__class__.__name__}")

    def test_upsert_bulk_update_path(self):
        self.db.insert_entity(self.entity)
        upserted, modified = self.db.upsert_entities_bulk([self.entity_updated])
        self.assertEqual(modified, 1, f"UPSERT-BULK modified!=1 for {self.entity.__class__.__name__}")


class TestEPersonCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = EPerson(key="__test_P_Moses", display_en_name="Moses", display_heb_name="משה",
                              timePeriod=TimePeriod.Tanach, isWoman=False, isNonJew=False, isGroup=False,
                              roles=[RoleType.Prophet], **_COMMON)
        self.entity_updated = EPerson(key="__test_P_Moses", display_en_name="Moshe Rabbeinu", display_heb_name="משה רבנו",
                                      timePeriod=TimePeriod.Tanach, isWoman=False, isNonJew=False, isGroup=False,
                                      roles=[RoleType.Prophet, RoleType.Judge], **_COMMON)


class TestEPlaceCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = EPlace(key="__test_L_Jerusalem", display_en_name="Jerusalem", display_heb_name="ירושלים",
                             placeType=PlaceType.City, **_COMMON)
        self.entity_updated = EPlace(key="__test_L_Jerusalem", display_en_name="Yerushalayim", display_heb_name="ירושלים",
                                     placeType=PlaceType.City, **_COMMON)


class TestENationCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = ENation(key="__test_N_Egypt", display_en_name="Egypt", display_heb_name="מצרים", **_COMMON)
        self.entity_updated = ENation(key="__test_N_Egypt", display_en_name="Mitzrayim", display_heb_name="מצרים", **_COMMON)


class TestEAnimalCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = EAnimal(key="__test_A_Lion", display_en_name="Lion", display_heb_name="אריה", **_COMMON)
        self.entity_updated = EAnimal(key="__test_A_Lion", display_en_name="Aryeh", display_heb_name="אריה", **_COMMON)


class TestEFoodCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = EFood(key="__test_F_Manna", display_en_name="Manna", display_heb_name="מן", **_COMMON)
        self.entity_updated = EFood(key="__test_F_Manna", display_en_name="Man", display_heb_name="מן", **_COMMON)


class TestEPlantCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = EPlant(key="__test_B_Olive", display_en_name="Olive", display_heb_name="זית", **_COMMON)
        self.entity_updated = EPlant(key="__test_B_Olive", display_en_name="Zayit", display_heb_name="זית", **_COMMON)


class TestESymbolCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = ESymbol(key="__test_S_Ark", display_en_name="Ark of Covenant", display_heb_name="ארון הברית",
                              symbolType=SymbolType.HolyObject, **_COMMON)
        self.entity_updated = ESymbol(key="__test_S_Ark", display_en_name="Aron HaBrit", display_heb_name="ארון הברית",
                                      symbolType=SymbolType.HolyObject, **_COMMON)


class TestENumberCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = ENumber(key="__test_M_70Elders", display_en_name="70", display_heb_name="שבעים",
                              numberCategory=NumberCategory.People, unit="elder", context="seventy elders", **_COMMON)
        self.entity_updated = ENumber(key="__test_M_70Elders", display_en_name="Seventy", display_heb_name="שבעים",
                                      numberCategory=NumberCategory.People, unit="elder", context="seventy elders of Israel", **_COMMON)


class TestETribeOfIsraelCRUD(EntityCRUDBase):
    def setUp(self):
        super().setUp()
        self.entity = ETribeOfIsrael(key="__test_T_Judah", display_en_name="Judah", display_heb_name="יהודה", **_COMMON)
        self.entity_updated = ETribeOfIsrael(key="__test_T_Judah", display_en_name="Yehuda", display_heb_name="יהודה", **_COMMON)


if __name__ == "__main__":
    unittest.main()



