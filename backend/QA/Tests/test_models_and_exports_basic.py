import unittest

from backend.db import mongo_parts
from backend.models.EntityObjects.EAnimal import EAnimal
from backend.models.EntityObjects.EFood import EFood
from backend.models.EntityObjects.ENation import ENation
from backend.models.EntityObjects.ENumber import ENumber
from backend.models.EntityObjects.EPerson import EPerson
from backend.models.EntityObjects.EPlace import EPlace
from backend.models.EntityObjects.EPlant import EPlant
from backend.models.EntityObjects.ESymbol import ESymbol
from backend.models.EntityObjects.ETribeOfIsrael import ETribeOfIsrael
from backend.models.Enums import (
    EntityType,
    NumberCategory,
    PlaceType,
    RelType,
    RoleType,
    SourceType,
    SymbolType,
    TimePeriod,
)
from backend.models.Rel import Rel
from backend.models.SourceClasses.SourceContent import SourceContent
from backend.models.SourceClasses.SourceMetadata import SourceMetadata


class ModelsAndExportsBasicTests(unittest.TestCase):
    def test_mongo_parts_init_exports_mixins(self):
        self.assertTrue(hasattr(mongo_parts, "EntityMongoMixin"))
        self.assertTrue(hasattr(mongo_parts, "RelationshipMongoMixin"))
        self.assertTrue(hasattr(mongo_parts, "SourceMetadataMongoMixin"))
        self.assertTrue(hasattr(mongo_parts, "SourceContentMongoMixin"))
        self.assertTrue(hasattr(mongo_parts, "FaissMongoMixin"))

    def test_entity_subclasses_instantiate_with_expected_entity_type(self):
        common_kwargs = {
            "display_en_name": "name",
            "display_heb_name": "name_he",
            "all_en_names": ["name"],
            "all_heb_names": ["name_he"],
        }

        entities = [
            EAnimal(key="A_lion", **common_kwargs),
            EFood(key="F_bread", **common_kwargs),
            ENation(key="N_nation", **common_kwargs),
            ENumber(key="M_40", numberCategory=NumberCategory.Time, unit="year", context="wandering", **common_kwargs),
            EPerson(
                key="P_moses",
                timePeriod=TimePeriod.Tanach,
                isWoman=False,
                isNonJew=False,
                roles=[RoleType.Prophet],
                **common_kwargs,
            ),
            EPlace(key="L_jerusalem", placeType=PlaceType.City, **common_kwargs),
            EPlant(key="B_olive", **common_kwargs),
            ESymbol(key="S_staff", symbolType=SymbolType.HolyObject, **common_kwargs),
            ETribeOfIsrael(key="T_judah", **common_kwargs),
        ]

        self.assertEqual(entities[0].entityType, EntityType.EAnimal)
        self.assertEqual(entities[1].entityType, EntityType.EFood)
        self.assertEqual(entities[2].entityType, EntityType.ENation)
        self.assertEqual(entities[3].entityType, EntityType.ENumber)
        self.assertEqual(entities[4].entityType, EntityType.EPerson)
        self.assertEqual(entities[5].entityType, EntityType.EPlace)
        self.assertEqual(entities[6].entityType, EntityType.EPlant)
        self.assertEqual(entities[7].entityType, EntityType.ESymbol)
        self.assertEqual(entities[8].entityType, EntityType.ETribeOfIsrael)

    def test_entity_to_db_dict_excludes_transient_fields(self):
        person = EPerson(
            key="P_moses",
            display_en_name="Moses",
            display_heb_name="moshe",
            all_en_names=["Moses"],
            all_heb_names=["moshe"],
            timePeriod=TimePeriod.Tanach,
            isWoman=False,
            isNonJew=False,
        )
        person.spokeWith.append("P_aaron")

        db_dict = person.to_db_dict()
        full_dict = person.to_full_dict()

        self.assertNotIn("spokeWith", db_dict)
        self.assertIn("spokeWith", full_dict)
        self.assertIn("key", db_dict)

    def test_rel_to_db_dict_excludes_transient_fields(self):
        rel = Rel(key="R_1", term1="P_1", term2="P_2", rel_type=RelType.spokeWith)
        rel.source_keys.extend(["TN_Genesis_1_1"])

        db_dict = rel.to_db_dict()
        full_dict = rel.to_full_dict()

        self.assertNotIn("source_keys", db_dict)
        self.assertIn("source_keys", full_dict)
        self.assertEqual(db_dict["rel_type"], RelType.spokeWith)

    def test_source_content_helpers(self):
        src = SourceContent(key="TN_Genesis_1_1", content=["<p>Hello</p>", "shalom", "Hello"])

        self.assertEqual(src.get_en_html_content(), "<p>Hello</p>")
        self.assertEqual(src.get_heb_html_content(), "shalom")
        self.assertIsInstance(src.get_clean_en_text(), str)
        self.assertIsInstance(src.get_clean_heb_text(), str)

    def test_source_metadata_defaults_and_types(self):
        metadata = SourceMetadata(source_type=SourceType.TN)
        metadata.key = "TN_Genesis_1_1"

        self.assertEqual(metadata.source_type, SourceType.TN)
        self.assertEqual(metadata.passage_types, [])
        self.assertEqual(metadata.entity_keys, set())
        self.assertEqual(metadata.rel_keys, set())


if __name__ == "__main__":
    unittest.main()



