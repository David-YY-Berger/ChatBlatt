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
