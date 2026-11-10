import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend.app.controllers.entity_search import entity_search_controller
from backend.models_db.Enums import PlaceType, RoleType, SymbolType, TimePeriod
from backend.models_dto.PersonSelectOption import PersonSelectOption
from backend.models_dto.PlaceSelectOption import PlaceSelectOption
from backend.models_dto.SymbolSelectOption import SymbolSelectOption


PEOPLE = [
    PersonSelectOption(
        key="alice", display_en_name="Alice", isWoman=True, isNonJew=False,
        isGroup=False, roles=[RoleType.King], timePeriod=TimePeriod.Tanach,
    ),
    PersonSelectOption(
        key="bob", display_en_name="Bob", isWoman=False, isNonJew=True,
        isGroup=True, roles=[RoleType.Prophet], timePeriod=TimePeriod.Tanaim,
    ),
    PersonSelectOption(key="unknown", display_en_name="Unknown"),
]


def _person_app(selector: str, lang: str = "en") -> AppTest:
    if selector == "entity":
        source = f"""
from pages.entity_search import _render_entity_search_tab
_render_entity_search_tab("people", {lang!r})
"""
    else:
        source = f"""
from components.person_selector import render_person_selector
render_person_selector({lang!r}, "test_center")
"""
    return AppTest.from_string(source, default_timeout=30)


def _names(app: AppTest) -> list[str]:
    return [label.split(" - ")[0] for label in app.selectbox[0].options]


class MetadataFilteringTests(unittest.TestCase):
    def test_people_role_and_period_filter_dropdown_on_both_selectors(self):
        handler = SimpleNamespace(get_select_options=lambda: PEOPLE)
        with patch.object(entity_search_controller, "get_entity_search_handler", return_value=handler):
            for selector in ("entity", "tree"):
                for lang in ("en", "he"):
                    with self.subTest(selector=selector, lang=lang):
                        app = _person_app(selector, lang).run()
                        self.assertEqual(_names(app), ["Alice", "Bob", "Unknown"])
                        app.multiselect[0].select(RoleType.King).run()
                        self.assertEqual(_names(app), ["Alice"])
                        app.multiselect[0].select(RoleType.Prophet).run()
                        self.assertEqual(_names(app), ["Alice", "Bob"])
                        app.multiselect[1].select(TimePeriod.Tanaim).run()
                        self.assertEqual(_names(app), ["Bob"])
                        app.multiselect[1].set_value([]).run()
                        app.multiselect[0].set_value([]).run()
                        self.assertEqual(_names(app), ["Alice", "Bob", "Unknown"])
                        self.assertFalse(app.exception)

    def test_people_boolean_filters_exclude_unknown_and_combine(self):
        handler = SimpleNamespace(get_select_options=lambda: PEOPLE)
        with patch.object(entity_search_controller, "get_entity_search_handler", return_value=handler):
            for selector, prefix in (
                ("entity", "filter_person"),
                ("tree", "person_selector_filter_test_center"),
            ):
                for field, selected, expected in (
                    ("religion", "jewish", ["Alice"]),
                    ("religion", "non_jewish", ["Bob"]),
                    ("gender", "women", ["Alice"]),
                    ("gender", "men", ["Bob"]),
                    ("group", "individual", ["Alice"]),
                    ("group", "group", ["Bob"]),
                ):
                    with self.subTest(selector=selector, field=field, selected=selected):
                        app = _person_app(selector).run()
                        app.session_state[f"{prefix}_{field}"] = selected
                        app.run()
                        self.assertEqual(_names(app), expected)
                        app.session_state[f"{prefix}_{field}"] = "all"
                        app.run()
                        self.assertEqual(_names(app), ["Alice", "Bob", "Unknown"])
                        self.assertFalse(app.exception)

                app = _person_app(selector).run()
                app.session_state[f"{prefix}_gender"] = "women"
                app.session_state[f"{prefix}_religion"] = "non_jewish"
                app.run()
                self.assertEqual(app.selectbox[0].options, [])
                self.assertTrue(app.warning)
                self.assertFalse(app.exception)

    def test_place_and_symbol_types_filter_dropdown(self):
        for tab, options, member, expected in (
            ("places", [
                PlaceSelectOption(key="city", display_en_name="City", placeType=PlaceType.City),
                PlaceSelectOption(key="desert", display_en_name="Desert", placeType=PlaceType.Desert),
                PlaceSelectOption(key="unknown", display_en_name="Unknown"),
            ], PlaceType.City, "City"),
            ("symbols", [
                SymbolSelectOption(key="clothes", display_en_name="Clothes", symbolType=SymbolType.Clothing),
                SymbolSelectOption(key="weapon", display_en_name="Weapon", symbolType=SymbolType.Weapon),
                SymbolSelectOption(key="unknown", display_en_name="Unknown"),
            ], SymbolType.Clothing, "Clothes"),
        ):
            with self.subTest(tab=tab):
                handler = SimpleNamespace(get_select_options=lambda: options)
                app = AppTest.from_string(f"""
from pages.entity_search import _render_entity_search_tab
_render_entity_search_tab({tab!r}, "en")
""", default_timeout=30)
                with patch.object(entity_search_controller, "get_entity_search_handler", return_value=handler):
                    app.run()
                    self.assertEqual(len(app.selectbox[0].options), 3)
                    app.checkbox[0].uncheck().run()
                    self.assertEqual(app.selectbox[0].options, [])
                    app.checkbox[1 + list(type(member)).index(member)].check().run()
                    self.assertEqual(app.selectbox[0].options, [expected])
                    app.checkbox[0].check().run()
                    self.assertEqual(len(app.selectbox[0].options), 3)
                    self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
