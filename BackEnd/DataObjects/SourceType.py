from enum import Enum


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
