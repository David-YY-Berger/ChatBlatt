from abc import ABC
from dataclasses import dataclass
from functools import total_ordering
from typing import Any

from backend.models.Enums import SourceType
from backend.models.SourceClasses.SectionSorting import get_section_sort_key

""" must be init w key"""
@total_ordering
@dataclass
class SourceClass(ABC):
    # example key: BT_Bava Batra_0_13b:9-14a:4 , or TN_Joshua_0_2:1–24
    key: str # (src_type:SourceType _ book:str _ chapter:int _ section:str)

    def __init__(self, key:str):
        self.key = key

    ################################################## Sorting ############################################

    def sort_key(self):
        """Return a tuple used for canonical ordering:
        (book.order, section_sort_key)
        """
        from backend.db.data_names.Books import Books
        book = self.get_book_from_key(self.key)
        book_order = book.order if book else 0
        src_type_name = self.key[:2] if self.key else ""
        section = self.get_section_from_key(self.key) if self.key else ""
        return (book_order, get_section_sort_key(src_type_name, section))

    def __eq__(self, other):
        if not isinstance(other, SourceClass):
            return NotImplemented
        return self.key == other.key

    def __lt__(self, other):
        if not isinstance(other, SourceClass):
            return NotImplemented
        return self.sort_key() < other.sort_key()

    def __hash__(self):
        return hash(self.key)

    ################################################## Getters ############################################

    def get_key(self) -> str:
        return self.key

    def get_src_type(self) -> SourceType | str | None:
        if self.key:
            return self.get_src_type_from_key(self.key)
        else:
            return None

    def get_book(self):
        """Returns the Book object for this source, or None if not found."""
        if self.key:
            return self.get_book_from_key(self.key)
        else:
            return None

    def get_book_name(self) -> str:
        """Returns the book's database_name string."""
        book = self.get_book()
        return book.database_name if book else ""

    def get_chapter(self) -> int:
        if self.key:
            return self.get_chapter_from_key(self.key)
        else:
            return 0

    def get_chapter_str(self) -> str:
        return "" if self.get_chapter() == 0 else str(self.get_chapter())

    def get_section(self) -> str:
        if self.key:
            return self.get_section_from_key(self.key)
        else:
            return ""


    ################################################## to_ methods ############################################

    def to_dict(self) -> dict[str, Any]:
        """Convert the Source object to a dictionary"""
        book = self.get_book()
        return {
            "src_type": str(self.get_src_type()),  # stringify enum
            "book": book.database_name if book else "",
            "chapter": self.get_chapter(),
            "section": self.get_section(),
        }

    def __str__(self) -> str:
        book = self.get_book()
        book_name = book.database_name if book else ""
        return f"{book_name} {self.get_section()} {self.get_chapter_str()} ({self.get_key()})"

    ################################################## misc ############################################

    def is_valid_else_get_error_list(self) -> list[str]:
        """Validate the Source object and return a list of error messages if invalid"""
        errors = []

        if not self.get_book_name().strip():
            errors.append("Book is null or empty!")

        if not isinstance(self.get_chapter(), int) or self.get_chapter() < 0:
            errors.append("Chapter must be a non-negative integer!")

        if not self.get_section().strip():
            errors.append("Section is null or empty!")

        return errors

    @staticmethod
    def get_collection_name_from_key(key: str) -> str:
        src_type = SourceClass.get_src_type_from_key(key)
        if src_type:
            return src_type.name
        else:
            return ""

    @staticmethod
    def get_src_type_from_key(key: str) -> SourceType | None:
        prefix = key[:2]
        return SourceType[prefix] if prefix in SourceType.__members__ else None

    @staticmethod
    def get_book_from_key(key):
        """Return the Book object corresponding to the book name in the key.
        Falls back to None if the book is not found in the registry.
        """
        from backend.db.data_names.Books import Books
        parts = key.split("_")
        if len(parts) < 2:
            return None
        db_name = parts[1]
        return Books.get_by_db_name(db_name)

    @staticmethod
    def get_book_name_from_key(key) -> str:
        """Convenience: return just the book database_name string from a key."""
        parts = key.split("_")
        if len(parts) < 2:
            return ""
        return parts[1]

    @staticmethod
    def get_chapter_from_key(key) -> int:
        parts = key.split("_")
        if len(parts) < 3:
            return 0
        else:
            return int(parts[2])

    @staticmethod
    def get_section_from_key(key) -> str:
        parts = key.split("_")
        if len(parts) < 4:
            return ""
        else:
            return parts[3]

    @staticmethod
    def get_key_from_details(src_type: SourceType, book: str, chapter: int, section: str) -> str:
        if not src_type:
            raise ValueError("src_type must be specified")

        book = book or "no book"
        chapter = chapter or "0"
        section = section or "no section"

        return f"{src_type.name}_{book}_{chapter}_{section}"