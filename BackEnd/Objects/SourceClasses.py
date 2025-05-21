import json
from enum import Enum
from dataclasses import dataclass, asdict, field


class SourceContentType(Enum):
    EN = 0
    HEB = 1

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


@dataclass
class Source:
    src_type: SourceType
    book: str
    chapter: int = 0
    section: str = ""
    content: list[str] = field(default_factory=list)

    def __post_init__(self):
        # Ensure chapter is an int (handle `None` or falsy)
        if not self.chapter:
            self.chapter = 0

    def get_key(self) -> str:
        return f"{self.src_type.name}_{self.book}_{self.chapter}_{self.section}"

    def to_dict(self):
        """Convert the Source object to a dictionary"""
        data = asdict(self) # is there an issue here? <
        data["src_type"] = str(self.src_type)
        return data

    def to_json(self):
        """Convert the Source object to a JSON string"""
        return json.dumps(self.to_dict())

    def is_valid_else_get_error_list(self) -> list[str]:
        errors = []

        if not self.book:
            errors.append("Book is null or empty!")

        if not isinstance(self.chapter, int) or self.chapter < 0:
            errors.append("Chapter must be a non-negative integer!")

        if not self.section:
            errors.append("Section is null or empty!")

        if not isinstance(self.content, list) or not all(isinstance(item, str) for item in self.content):
            errors.append("Content must be a list of strings!")
        elif not any(item.strip() for item in self.content):
            errors.append("Content must contain at least one non-empty string!")

        return errors