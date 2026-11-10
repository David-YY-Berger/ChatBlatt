import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from frontend import app
from components.facets import renderers
from backend.models_db.Enums import EntityType
from pages.entity_search import _ENTITY_ICONS, _entity_type_to_tab
from system_common.Constants import PAGE_SYMBOLS


class HiddenSymbolsUITests(unittest.TestCase):
    def test_source_search_facets_do_not_render_symbols(self):
        rendered_entity_keys = []
        with (
            patch.object(renderers, "preload_all_entity_options"),
            patch.object(
                renderers,
                "_render_entity_select_panel",
                side_effect=lambda ent, lang: rendered_entity_keys.append(ent["key"]),
            ),
        ):
            result = AppTest.from_string(
                "from components.facets.renderers import render_entity_facets\n"
                "render_entity_facets('en')"
            ).run()

        self.assertNotIn("symbol", rendered_entity_keys)
        self.assertTrue(rendered_entity_keys)
        self.assertFalse(result.exception)

    def test_entity_search_controls_hide_symbols(self):
        result = AppTest.from_string(
            "from pages.entity_search import _render_entity_type_selector\n"
            "_render_entity_type_selector(None, 'en')"
        ).run()

        self.assertEqual(len(result.button), 4)
        self.assertNotIn(PAGE_SYMBOLS, [tab for tab, _ in _ENTITY_ICONS])
        self.assertIsNone(_entity_type_to_tab(EntityType.ESymbol))
        self.assertFalse(result.exception)

    def test_symbols_page_is_not_in_entity_navigation(self):
        created_pages = []
        streamlit = MagicMock()

        def make_page(*args, **kwargs):
            page = MagicMock()
            page.title = kwargs["title"]
            page.url_path = kwargs["url_path"]
            created_pages.append(page)
            return page

        streamlit.Page.side_effect = make_page
        with (
            patch.object(app, "st", streamlit),
            patch.object(app, "_render_mobile_menu"),
        ):
            app._build_navigation("en")

        groups = streamlit.navigation.call_args.args[0]
        entity_group = next(
            pages
            for pages in groups.values()
            if pages[0].url_path == app.URL_PATHS[app.PAGE_ENTITY_SEARCH]
        )
        symbol_page = next(
            page for page in created_pages if page.url_path == app.URL_PATHS[PAGE_SYMBOLS]
        )
        self.assertNotIn(symbol_page, entity_group)


if __name__ == "__main__":
    unittest.main()
