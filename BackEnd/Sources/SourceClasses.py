import json
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Any, Optional


class SourceContentType(Enum):
    EN = 0
    HEB = 1
    EN_CLEAN = 2

class SourceType(Enum):
    # DONT CHANGE THESE ABBREVIATTIONS! hardcoded in MondoDB impl
    BT = (0, "Babylonian Talmud")
    JT = (1, "Jerusalem Talmud")
    RM = (2, "Rambam Mishne Torah")
    TN = (3, "Tanach")
    MS = (4, "Mishna")

    def __new__(cls, value, description):
        # Create the new enum instance
        obj = object.__new__(cls)
        # Assign the integer value
        obj._value_ = value
        # Assign the description as a custom attribute
        obj.description = description
        return obj

    def __str__(self):
        return self.description

''' can be init with either the key, or src_type&book&chapter&section'''
@dataclass
class Source:
    src_type: SourceType | None = None
    key: str = ""
    #example key: BT_Bava Batra_0_13b:9-14a:4 , or
    book: str = ""
    chapter: int = 0
    section: str = ""
    summary: str = ""
    content: list[str] = field(default_factory=list)
    filters: list[list[int]] = field(default_factory=list)

    def __post_init__(self):
        # Ensure chapter is an int (handle `None` or falsy)
        if not self.chapter:
            self.chapter = 0

    def get_key(self) -> str:
        if self.key:
            return self.key
        elif self.src_type and self.book and self.section:
            return f"{self.src_type.name}_{self.book}_{self.chapter}_{self.section}"
        else:
            # Collect non-empty parts
            parts = []
            if self.book:
                parts.append(str(self.book))
            if self.chapter:  # chapter is int, skip if 0
                parts.append(str(self.chapter))
            if self.section:
                parts.append(str(self.section))

            if parts:
                return f"no key found for {' '.join(parts)}"
            else:
                return "no key found"

    def get_src_type(self) -> SourceType | str | None:
        if self.src_type:
            return self.src_type
        elif self.key:
            return Source.get_source_type_from_key(self.key)
        else:
            return None

    def get_book(self) -> str:
        if self.book:
            return self.book
        elif self.key:
            return Source.get_book_from_key(self.key)
        else:
            return ""

    def get_section(self) -> str:
        if self.section:
            return self.section
        elif self.key:
            return Source.get_section_from_key(self.key)
        else:
            return ""


    def to_dict(self) -> dict[str, Any]:
        """Convert the Source object to a dictionary"""
        return {
            "src_type": str(self.src_type),  # stringify enum
            "summary": self.summary,
            "book": self.book,
            "chapter": self.chapter,
            "section": self.section,
            "content": self.content,
            "filters": self.filters,
        }

    def to_json(self) -> str:
        """Convert the Source object to a JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def is_valid_else_get_error_list(self) -> list[str]:
        """Validate the Source object and return a list of error messages if invalid"""
        errors = []

        if not self.book.strip():
            errors.append("Book is null or empty!")

        if not isinstance(self.chapter, int) or self.chapter < 0:
            errors.append("Chapter must be a non-negative integer!")

        if not self.section.strip():
            errors.append("Section is null or empty!")

        if not isinstance(self.content, list) or not all(isinstance(item, str) for item in self.content):
            errors.append("Content must be a list of strings!")
        elif not any(item.strip() for item in self.content):
            errors.append("Content must contain at least one non-empty string!")

        if not isinstance(self.filters, list) or not all(
                isinstance(sublist, list) and all(isinstance(i, int) for i in sublist)
                for sublist in self.filters
        ):
            errors.append("Filters must be a list of lists of integers!")

        return errors

    @staticmethod
    def get_collection_name_from_key(key: str) -> str:
        src_type = Source.get_source_type_from_key(key)
        if src_type:
            return src_type.name
        else:
            return ""

    @staticmethod
    def get_source_type_from_key(key: str) -> SourceType | None:
        prefix = key[:2]
        return SourceType[prefix] if prefix in SourceType.__members__ else None

    @staticmethod
    def get_book_from_key(key) -> str:
        parts = key.split("_")
        if len(parts) < 2:
            return ""
        else:
            return parts[1]

    @staticmethod
    def get_chapter_from_key(key) -> str:
        parts = key.split("_")
        if len(parts) < 3:
            return ""
        else:
            return parts[2]

    @staticmethod
    def get_section_from_key(key) -> str:
        parts = key.split("_")
        if len(parts) < 4:
            return ""
        else:
            return parts[3]