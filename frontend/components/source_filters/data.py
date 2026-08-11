# bs"d - lehagdil torah velahadir
"""Book-grouping helpers for the source-filters tree (Source Type -> Book
Category -> Book)."""

from __future__ import annotations

from backend.db.data_names.Books import Book, Books
from backend.models_db.Enums import BookCategoryName, SourceType


def group_books_by_source_then_category() -> dict[SourceType, dict[BookCategoryName, list[Book]]]:
    """Return ``{SourceType: {BookCategoryName: [Book, ...]}}`` in sorted order."""
    result: dict[SourceType, dict[BookCategoryName, list[Book]]] = {}
    for b in Books.sorted_all():
        result.setdefault(b.source_type, {})
        result[b.source_type].setdefault(b.category, [])
        result[b.source_type][b.category].append(b)
    return result
