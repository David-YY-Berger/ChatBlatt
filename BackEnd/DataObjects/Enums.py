# bs"d - lehagdil torah velahadir

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
    Tanach = (0, "Tanach Era") # add more eras thoughout tanach...
    Tanaim = (1, "Tanaim")
    Amoraim = (2, "Amoraim")
    NoTimePeriod = (3, "No Time Period")

class SymbolType(DescribedEnum):
    Clothing = (2, "Clothing")
    HolyObject = (5, "Holy Object")

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
    EPerson = ("P", "Person/Group")  # Includes individuals AND groups (e.g., "the 70 elders")
    EPlace  = ("L", "Place")
    ETribeOfIsrael  = ("T", "TribeOfIsrael")
    ENation = ("N", "Nation")
    ESymbol = ("S", "Symbol")
    ENumber = ("M", "Number")
    EAnimal = ("A", "Animal")  # Real and mythical animals
    EFood = ("F", "Food")  # Food items
    EPlant = ("B", "Plant")  # Plants (edible and inedible)

class RelType(DescribedEnum):
    # Person/Group → Person/Group
    studiedFrom = ("PP01", "studiedFrom")
    childOfFather = ("PP03", "childOfFather")
    childOfMother = ("PP08", "childOfMother")
    spouseOf = ("PP04", "spouseOf")
    descendantOf = ("PP05", "descendantOf")
    spokeWith = ("PP06", "spokeWith")
    disagreedWith = ("PP07", "disagreedWith")

    # Person/Group → {anything}
    prophesiedAbout = ("PX01", "prophesiedAbout")

    # Person/Group → Place
    bornIn = ("PL01", "bornIn")
    diedIn = ("PL02", "diedIn")
    prayedAt = ("PL03", "prayedAt")
    visited = ("PL04", "visited")
    associatedWithPlace = ("PL05", "associatedWithPlace")  # Person/Symbol → Place fallback

    # Symbol → Place
    symbolAssociatedWithPlace = ("SL01", "symbolAssociatedWithPlace")

    # Person/Group → TribeOfIsrael
    personToTribeOfIsrael = ("PT01", "personToTribeOfIsrael")

    # Person/Group → Nation
    personBelongsToNation = ("PN01", "personBelongsToNation")

    # Nation → Nation, or Person/Group → Person/Group
    enemyOf = ("NN01", "enemyOf")
    allyOf = ("NN02", "allyOf")

    # Place → Nation
    placeToNation = ("LN01", "placeToNation")

    # {anything} → {anything}
    comparedTo = ("XS01", "comparedTo")
    contrastedWith = ("XS02", "contrastedWith")
    AliasOf = ("XS03", "AliasOf")



class SourceContentType(Enum):
    EN = 0
    HEB = 1
    EN_CLEAN = 2
