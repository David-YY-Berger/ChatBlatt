# bs"d
"""
Tests for SourceClass / SourceContent sorting logic.

Covers:
- BT folio section sorting (e.g. 3b:4, 14a:11, 14b:5, 19a:11)
- TN chapter:verse section sorting (e.g. 1:1–24, 2:1–24, 5:13–6:27)
- Cross-book sorting by Book.order
- Integration: get_all_src_contents_by_book returns sorted results
"""
import unittest

from backend.models_db.SourceClasses.SectionSorting import (
    bt_section_sort_key,
    tn_section_sort_key,
    get_section_sort_key,
)
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend.db.data_names.Books import Books


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests: Section sort-key functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestBTSectionSorting(unittest.TestCase):
    """BT uses folio notation: page + a/b side + optional line number."""

    def test_basic_order(self):
        sections = ["14b:5-8", "3b:4-7", "14a:11-14b:3", "19a:11"]
        expected = ["3b:4-7", "14a:11-14b:3", "14b:5-8", "19a:11"]
        result = sorted(sections, key=bt_section_sort_key)
        self.assertEqual(result, expected)

    def test_a_before_b_same_page(self):
        self.assertLess(bt_section_sort_key("14a:1"), bt_section_sort_key("14b:1"))

    def test_line_ordering_same_folio(self):
        self.assertLess(bt_section_sort_key("14b:3"), bt_section_sort_key("14b:10"))

    def test_range_sorts_by_start(self):
        # "13b:9-14a:4" starts at 13b:9
        self.assertLess(bt_section_sort_key("13b:9-14a:4"), bt_section_sort_key("14a:1"))

    def test_single_ref_no_line(self):
        # "19a" with no line defaults to line 0
        key = bt_section_sort_key("19a")
        self.assertEqual(key, (19, 0, 0))

    def test_mixed_formats(self):
        sections = ["2a:1", "2b:5-8", "2a:10", "3a:1", "2b:1"]
        expected = ["2a:1", "2a:10", "2b:1", "2b:5-8", "3a:1"]
        result = sorted(sections, key=bt_section_sort_key)
        self.assertEqual(result, expected)


class TestTNSectionSorting(unittest.TestCase):
    """TN uses chapter:verse with en-dash or hyphen ranges."""

    def test_basic_order(self):
        sections = ["5:13\u20136:27", "1:1\u201324", "18:1\u201318:10", "2:1\u201324"]
        expected = ["1:1\u201324", "2:1\u201324", "5:13\u20136:27", "18:1\u201318:10"]
        result = sorted(sections, key=tn_section_sort_key)
        self.assertEqual(result, expected)

    def test_same_chapter_verse_order(self):
        sections = ["3:10-20", "3:1-5", "3:5-9"]
        expected = ["3:1-5", "3:5-9", "3:10-20"]
        result = sorted(sections, key=tn_section_sort_key)
        self.assertEqual(result, expected)

    def test_en_dash_and_hyphen_equivalent(self):
        # en-dash \u2013 and regular hyphen should parse identically
        key_dash = tn_section_sort_key("5:13\u20136:27")
        key_hyphen = tn_section_sort_key("5:13-6:27")
        self.assertEqual(key_dash, key_hyphen)

    def test_single_ref(self):
        key = tn_section_sort_key("12:5")
        self.assertEqual(key, (12, 5))


class TestGenericSortKeyDispatch(unittest.TestCase):
    """get_section_sort_key dispatches correctly by source type name."""

    def test_bt_dispatch(self):
        key = get_section_sort_key("BT", "14b:5-8")
        self.assertEqual(key, bt_section_sort_key("14b:5-8"))

    def test_tn_dispatch(self):
        key = get_section_sort_key("TN", "5:13\u20136:27")
        self.assertEqual(key, tn_section_sort_key("5:13\u20136:27"))

    def test_unknown_type_uses_fallback(self):
        # Should not raise, falls back to generic
        key = get_section_sort_key("XX", "123-456")
        self.assertIsInstance(key, tuple)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests: SourceContent sorting via __lt__
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceContentSorting(unittest.TestCase):
    """SourceContent objects should be sortable by book order then section."""

    def _make(self, key):
        return SourceContent(key=key, content=["en", "heb", ""])

    def test_bt_sources_sort_by_section(self):
        keys = [
            "BT_Bava Batra_0_13b:9-14a:4",
            "BT_Bava Batra_0_3b:4-7",
            "BT_Bava Batra_0_7b:6-7",
        ]
        sources = [self._make(k) for k in keys]
        sources.sort()
        sorted_keys = [s.key for s in sources]
        expected = [
            "BT_Bava Batra_0_3b:4-7",
            "BT_Bava Batra_0_7b:6-7",
            "BT_Bava Batra_0_13b:9-14a:4",
        ]
        self.assertEqual(sorted_keys, expected)

    def test_tn_sources_sort_by_section(self):
        keys = [
            "TN_Genesis_0_6:14-25",
            "TN_Genesis_0_1:1-5",
            "TN_Genesis_0_3:1-24",
        ]
        sources = [self._make(k) for k in keys]
        sources.sort()
        sorted_keys = [s.key for s in sources]
        expected = [
            "TN_Genesis_0_1:1-5",
            "TN_Genesis_0_3:1-24",
            "TN_Genesis_0_6:14-25",
        ]
        self.assertEqual(sorted_keys, expected)

    def test_cross_book_sorting_bt(self):
        """Berakhot (order=1) should come before Bava Batra (order=23)."""
        src_bb = self._make("BT_Bava Batra_0_3b:4-7")
        src_ber = self._make("BT_Berakhot_0_10a:1")
        sources = [src_bb, src_ber]
        sources.sort()
        self.assertEqual(sources[0].key, "BT_Berakhot_0_10a:1")
        self.assertEqual(sources[1].key, "BT_Bava Batra_0_3b:4-7")

    def test_cross_book_sorting_tn(self):
        """Genesis (order=1) should come before Joshua (order=6)."""
        src_josh = self._make("TN_Joshua_0_2:1-24")
        src_gen = self._make("TN_Genesis_0_50:1-26")
        sources = [src_josh, src_gen]
        sources.sort()
        self.assertEqual(sources[0].key, "TN_Genesis_0_50:1-26")
        self.assertEqual(sources[1].key, "TN_Joshua_0_2:1-24")

    def test_bt_full_sequence(self):
        """A larger BT sequence to ensure correctness."""
        keys = [
            "BT_Sanhedrin_0_96b:2-9",
            "BT_Sanhedrin_0_2a:1-5",
            "BT_Sanhedrin_0_19a:11",
            "BT_Sanhedrin_0_14b:5-8",
            "BT_Sanhedrin_0_14a:11-14b:3",
        ]
        sources = [self._make(k) for k in keys]
        sources.sort()
        sorted_keys = [s.key for s in sources]
        expected = [
            "BT_Sanhedrin_0_2a:1-5",
            "BT_Sanhedrin_0_14a:11-14b:3",
            "BT_Sanhedrin_0_14b:5-8",
            "BT_Sanhedrin_0_19a:11",
            "BT_Sanhedrin_0_96b:2-9",
        ]
        self.assertEqual(sorted_keys, expected)


# ═══════════════════════════════════════════════════════════════════════════════
# Integration test: get_all_src_contents_by_book returns sorted
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAllSrcContentsByBookSorted(unittest.TestCase):
    """Ensure the DB mixin returns SourceContents in sorted order."""

    def setUp(self):
        from backend.QA.Tests.conftest import FakeDBapi
        self.db = FakeDBapi.create()

    def _insert(self, book, keys):
        from backend.db.Collections import CollectionObjs
        col = CollectionObjs.get_col_obj_from_str(book.source_type.name)
        for k in keys:
            self.db.get_collection(col).insert_one({"key": k, "content": ["en", "heb", ""]})

    def test_bt_book_returns_sorted(self):
        keys_shuffled = [
            "BT_Bava Batra_0_13b:9-14a:4",
            "BT_Bava Batra_0_3b:4-7",
            "BT_Bava Batra_0_19a:11",
            "BT_Bava Batra_0_7b:6-7",
        ]
        self._insert(Books.BAVA_BATRA, keys_shuffled)
        results = self.db.get_all_src_contents_by_book(Books.BAVA_BATRA)
        result_keys = [r.key for r in results]
        expected = [
            "BT_Bava Batra_0_3b:4-7",
            "BT_Bava Batra_0_7b:6-7",
            "BT_Bava Batra_0_13b:9-14a:4",
            "BT_Bava Batra_0_19a:11",
        ]
        self.assertEqual(result_keys, expected)

    def test_tn_book_returns_sorted(self):
        keys_shuffled = [
            "TN_Genesis_0_6:14-25",
            "TN_Genesis_0_1:1-5",
            "TN_Genesis_0_12:1-9",
            "TN_Genesis_0_3:1-24",
        ]
        self._insert(Books.GENESIS, keys_shuffled)
        results = self.db.get_all_src_contents_by_book(Books.GENESIS)
        result_keys = [r.key for r in results]
        expected = [
            "TN_Genesis_0_1:1-5",
            "TN_Genesis_0_3:1-24",
            "TN_Genesis_0_6:14-25",
            "TN_Genesis_0_12:1-9",
        ]
        self.assertEqual(result_keys, expected)


if __name__ == "__main__":
    unittest.main()

