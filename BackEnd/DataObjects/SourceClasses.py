import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

from BackEnd.DataObjects.SourceType import SourceType


class SourceContentType(Enum):
    EN = 0
    HEB = 1
    EN_CLEAN = 2


''' must be init w key (can generate key from src_type & book & chapter & section)'''
@dataclass
class Source:
    # example key: BT_Bava Batra_0_13b:9-14a:4 , or TN_Joshua_0_2:1–24
    key: str # (src_type:SourceType _ book:str _ chapter:int _ section:str)
    summary: str = ""
    content: list[str] = field(default_factory=list)

    ################################################## Getters ############################################

    def get_key(self) -> str:
        return self.key

    def get_src_type(self) -> SourceType | str | None:
        if self.key:
            return Source.get_source_type_from_key(self.key)
        else:
            return None

    def get_book(self) -> str:
        if self.key:
            return Source.get_book_from_key(self.key)
        else:
            return ""

    def get_chapter(self) -> int:
        if self.key:
            return Source.get_chapter_from_key(self.key)
        else:
            return 0

    def get_chapter_str(self) -> str:
        return "" if self.get_chapter() == 0 else str(self.get_chapter())

    def get_section(self) -> str:
        if self.key:
            return Source.get_section_from_key(self.key)
        else:
            return ""

    def get_content(self) -> list[str]:
        return self.content

    def get_summary(self) -> str | None:
        return self.summary or "Summary PlaceHolder; no summary found for this source"

    ################################################## to_ methods ############################################

    def to_dict(self) -> dict[str, Any]:
        """Convert the Source object to a dictionary"""
        return {
            "src_type": str(self.get_src_type()),  # stringify enum
            "summary": self.summary,
            "book": self.get_book(),
            "chapter": self.get_book(),
            "section": self.get_section(),
            "content": self.content,
        }

    def to_json(self) -> str:
        """Convert the Source object to a JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def __str__(self) -> str:
        return f"{self.get_book()} {self.get_section()} {self.get_chapter_str()} - {self.get_summary()}"

    ################################################## misc ############################################

    def is_valid_else_get_error_list(self) -> list[str]:
        """Validate the Source object and return a list of error messages if invalid"""
        errors = []

        if not self.get_book().strip():
            errors.append("Book is null or empty!")

        if not isinstance(self.get_chapter(), int) or self.get_chapter() < 0:
            errors.append("Chapter must be a non-negative integer!")

        if not self.get_section().strip():
            errors.append("Section is null or empty!")

        if not isinstance(self.content, list) or not all(isinstance(item, str) for item in self.content):
            errors.append("Content must be a list of strings!")
        elif not any(item.strip() for item in self.content):
            errors.append("Content must contain at least one non-empty string!")

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

