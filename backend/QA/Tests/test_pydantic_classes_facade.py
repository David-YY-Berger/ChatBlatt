# bs'd
import unittest

from backend.models.Enums import NumberCategory
from backend.models.PydanticModels import PydanticClasses as pc


class PydanticClassesFacadeTests(unittest.TestCase):
    def test_facade_exports_expected_symbols(self):
        expected_symbols = {
            "Entity",
            "NumberEntity",
            "Entities",
            "Relation",
            "Relationships",
            "ExtractionResult",
            "FinalResponse",
            "smart_title_case",
            "_normalize_number_string",
            "TRIBES_OF_ISRAEL",
            "ENTITY_CATEGORIES",
            "NumberCategory",
        }

        self.assertTrue(expected_symbols.issubset(set(pc.__all__)))
        for symbol in expected_symbols:
            self.assertTrue(hasattr(pc, symbol), f"Missing facade symbol: {symbol}")

    def test_entity_and_relation_normalization(self):
        entity = pc.Entity(en_name="  putiel's daughter  ")
        relation = pc.Relation(term1="  moses ", term2=" aaron  ")

        self.assertEqual(entity.en_name, "Putiel's Daughter")
        self.assertEqual(relation.term1, "Moses")
        self.assertEqual(relation.term2, "Aaron")

    def test_number_entity_normalization_and_fallback(self):
        entities = pc.Entities(
            Number=[
                pc.NumberEntity(
                    en_name="thiry seven",
                    number_category="NotARealCategory",
                    unit="years",
                    context="wilderness census",
                )
            ]
        )

        self.assertIsNotNone(entities.Number)
        self.assertEqual(len(entities.Number), 1)

        number = entities.Number[0]
        self.assertEqual(number.en_name, "40")
        self.assertEqual(number.number_category, NumberCategory.Misc.description)
        self.assertEqual(number.unit, "year")

    def test_minimal_final_response_instantiation(self):
        res = pc.FinalResponse(
            res=pc.ExtractionResult(
                en_summary="moses leads people through desert trials",
                heb_summary="moses leads people through desert trials",
                passage_types=["STORY"],
                Entities=pc.Entities(Person=[pc.Entity(en_name="moses")]),
            )
        )

        self.assertEqual(res.res.en_summary, "moses leads people through desert trials")
        self.assertEqual(res.res.Entities.Person[0].en_name, "Moses")


if __name__ == "__main__":
    unittest.main()

