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

class SymbolType(DescribedEnum):
    Animal = (0, "Animal")
    Plant = (1, "Plant")
    Clothing = (2, "Clothing")
    HumanRelationship = (3, "Human Relationship")
    Food = (4, "Food")

class PlaceType(DescribedEnum):
    City = (0, "City")
    BodyOfWater = (1, "Body of Water")
    Mountain = (2, "Mountain")

class RoleType(DescribedEnum):
    Prophet = (1, "Prophet")
    King = (2, "King")
    Judge = (3, "Judge")
    Kohen = (4, "Kohen")
    Tanna = (5, "Tanna")
    Amora = (6, "Amora")
    Geon = (7, "Geon")
    Rishon = (8, "Rishon")
    Acharon = (9, "Acharon")

class EntityType(DescribedEnum):

    # todo might change this... as of now - refer to CSV until actually build this..

    EPerson      = (1, "Person", "A")
    # EPlace       = (2, "Place", "B")
    # ETribe       = (3, "Tribe", "C")
    # ENation      = (4, "Nation", "D")
    # EPassageType = (5, "PassageType", "E")
    # ESymbol      = (6, "Symbol", "F")

    # NERs / Relations
    # studiedFrom      = (8, "StudiedFrom", "H")

    def __new__(cls, value, description, key_pref):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        obj.keyPref = key_pref
        return obj

class RelType(DescribedEnum):
    # todo might change this... as of now - refer to CSV until actually build this..
    studiedFrom = (1, "StudiedFrom")


class SourceContentType(Enum):
    EN = 0
    HEB = 1
    EN_CLEAN = 2
