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

class PassageType(DescribedEnum):
    Law = (0, "Law")
    Story = (1, "Story")
    PHILOSOPHIC = (2, "PHILOSOPHIC")
    GENEALOGY = (3, "GENEALOGY")
    PROPHECY = (4, "PROPHECY")

class EntityType(DescribedEnum):
    EPerson = ("P", "Person")
    EPlace  = ("L", "Place")
    ETribeOfIsrael  = ("T", "TribeOfIsrael")
    ENation = ("N", "Nation")
    ESymbol = ("S", "Symbol")

class RelType(DescribedEnum):
    # Person → Person
    studiedFrom = ("PP01", "studiedFrom")
    siblingWith = ("PP02", "siblingWith")
    childOf = ("PP03", "childOf")
    spouseOf = ("PP04", "spouseOf")
    descendantOf = ("PP05", "descendantOf")

    # Person → Place
    bornIn = ("PL01", "bornIn")
    diedIn = ("PL02", "diedIn")
    visited = ("PL04", "visited")

    # Person → TribeOfIsrael
    personToTribeOfIsrael = ("PT01", "personToTribeOfIsrael")

    # Person → Nation
    personBelongsToNation = ("PN01", "personBelongsToNation")

    # Nation → Nation
    EnemyOf = ("NN01", "EnemyOf")
    AllyOf = ("NN02", "AllyOf")

    # Place → Nation
    placeToNation = ("LN01", "placeToNation")

    # {anything} → Symbol
    comparedTo = ("XS01", "comparedTo")
    contrastedWith = ("XS02", "contrastedWith")

    # {anything} → {anything}
    alias = ("XX01", 'alias')
    aliasFromSages = ("XX02", "aliasFromSages")



class SourceContentType(Enum):
    EN = 0
    HEB = 1
    EN_CLEAN = 2
