from dataclasses import dataclass, field
from typing import Any, List

from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass


@dataclass
class SourceContent(SourceClass):
    content: list[str] = field(default_factory=list)

    def __init__(self, key: str, content: List[str]):
        super().__init__(key)  # Initialize the base SourceClass
        self.content = content

    def get_content(self) -> list[str]:
        return self.content

    def is_valid_else_get_error_list(self) -> List[str]:
        # Get errors from parent
        errors = super().is_valid_else_get_error_list()

        # Validate content
        if not isinstance(self.content, list) or not all(isinstance(item, str) for item in self.content):
            errors.append("Content must be a list of strings!")
        elif not any(item.strip() for item in self.content):
            errors.append("Content must contain at least one non-empty string!")

        return errors
