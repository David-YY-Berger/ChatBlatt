from enum import Enum

class DescribedEnum(Enum):
    def __new__(cls, value, description):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        return obj

    def __str__(self):
        return self.description


class SourceType(DescribedEnum):
    # DONT CHANGE THESE ABBREVIATIONS! hardcoded in MongoDB impl
    BT = (0, "Babylonian Talmud")
    JT = (1, "Jerusalem Talmud")
    RM = (2, "Rambam Mishne Torah")
    TN = (3, "Tanach")
    MS = (4, "Mishna")


class TimePeriod(DescribedEnum):
    Tanach = (0, "Tanach Era")
    Tanaim = (1, "Tanaim")
    Amoraim = (2, "Amoraim")
    NoTimePeriod = (3, "No Time Period")


class EntityOrNERType(DescribedEnum):
    # Entities
    EPerson      = (1, "Person", "A")
    EPlace       = (2, "Place", "B")
    ETribe       = (3, "Tribe", "C")
    ENation      = (4, "Nation", "D")
    EPassageType = (5, "PassageType", "E")
    ESymbol      = (6, "Symbol", "F")
    EMitzvah     = (7, "Mitzvah", "G")

    # NERs / Relations
    studiedFrom      = (8, "StudiedFrom", "H")
    personToPlace    = (9, "PersonToPlace", "I")
    personToNation   = (10, "PersonToNation", "J")
    comparedTo       = (11, "ComparedTo", "K")
    taughtMitzvah    = (12, "TaughtMitzvah", "L")
    performedMitzvah = (13, "PerformedMitzvah", "M")

    def __new__(cls, value, description, key_pref):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        obj.keyPref = key_pref
        return obj

