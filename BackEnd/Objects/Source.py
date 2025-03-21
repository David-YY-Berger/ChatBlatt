import json
from enum import Enum


class SourceContentType(Enum):
    EN_CONTENT = 0
    HEB_CONTENT = 1

class SourceType(Enum):
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




class Source:
    def __init__(self, src_type : SourceType, book: str, chapter: int, section: str, content: list[str]):
        self.srcType = src_type
        self.book = book
        self.chapter = chapter or 0 #not always populated
        self.section = section
        self.content = content

    def get_key(self) -> str:
        return f"{self.type.name}_{self.book}_{self.chapter}_{self.section}"

    def to_dict(self):
        """Convert the Source object to a dictionary"""
        return {
            "srcType": str(self.srcType),  # Assuming you want to convert SourceType to a string
            "book": self.book,
            "chapter": self.chapter,
            "section": self.section,
            "content": self.content
        }

    def to_json(self):
        """Convert the Source object to a JSON string"""
        return json.dumps(self.to_dict())

    def is_valid_else_get_error_list(self):
        errors = []

        if not self.book:
            errors.append("Book is null or empty!")

        if not isinstance(self.chapter, int) or self.chapter < 0:
            errors.append("Chapter must be a non-negative integer!")

        if not self.section:
            errors.append("Section is null or empty!")

        if not isinstance(self.content, list) or not all(isinstance(item, str) for item in self.content):
            errors.append("Content must be a list of strings!")

        return errors