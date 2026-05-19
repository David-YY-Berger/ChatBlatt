# bs"d - lehagdil torah velahadir

from enum import Enum


class SourceType(Enum):
    BT = "Babylonian Talmud"
    JT = "Jerusalem Talmud"
    RM = "Rambam Mishne Torah"
    TN = "Tanach"
    MS = "Mishna"

class TimePeriod(Enum):
    Tanach = "Tanach"  # add more eras throughout tanach...
    Tanaim = "Tanaim"
    Amoraim = "Amoraim"
    NoTimePeriod = "No Time Period"

class SymbolType(Enum):
    Clothing = "Clothing"
    HolyObject = "Holy Object"

class PlaceType(Enum):
    City = "City"
    BodyOfWater = "Body of Water"
    Mountain = "Mountain"

class RoleType(Enum):
    Prophet = "Prophet"
    King = "King"
    Judge = "Judge"
    Kohen = "Kohen"
    Tanna = "Tanna"
    Amora = "Amora"
    Geon = "Geon"
    Rishon = "Rishon"
    Acharon = "Acharon"

class NumberCategory(Enum):
    Sacrifice = "Sacrifice"       # Offerings: animals, flour, oil, incense
    Time = "Time"                 # Duration, age, dates, periods
    Money = "Money"               # Currency, payment, value
    People = "People"             # Counts of persons, armies, tribes
    Measurement = "Measurement"   # Distance, weight, volume, area
    Misc = "Misc"                 # Anything not covered above

class PassageType(Enum):
    LAW = "Law"
    STORY = "Story"
    PHILOSOPHIC = "Philosophic"
    GENEALOGY = "Genealogy"
    PROPHECY = "Prophecy"

class EntityType(Enum):
    EPerson = "Person"          # Includes individuals AND groups (e.g., "the 70 elders")
    EPlace = "Place"
    ETribeOfIsrael = "TribeOfIsrael"
    ENation = "Nation"
    ESymbol = "Symbol"
    ENumber = "Number"
    EAnimal = "Animal"          # Real and mythical animals
    EFood = "Food"              # Food items
    EPlant = "Plant"            # Plants (edible and inedible)

class RelType(Enum):
    # Person/Group → Person/Group
    studiedFrom = "studiedFrom"
    childOfFather = "childOfFather"
    childOfMother = "childOfMother"
    spouseOf = "spouseOf"
    descendantOf = "descendantOf"
    spokeWith = "spokeWith"
    disagreedWith = "disagreedWith"

    # Person/Group → {anything}
    prophesiedAbout = "prophesiedAbout"

    # Person/Group → Place
    bornIn = "bornIn"
    diedIn = "diedIn"
    prayedAt = "prayedAt"
    visited = "visited"
    associatedWithPlace = "associatedWithPlace"  # Person/Symbol → Place fallback

    # Symbol → Place
    symbolAssociatedWithPlace = "symbolAssociatedWithPlace"

    # Person/Group → TribeOfIsrael
    personToTribeOfIsrael = "personToTribeOfIsrael"

    # Person/Group → Nation
    personBelongsToNation = "personBelongsToNation"

    # Nation → Nation, or Person/Group → Person/Group
    enemyOf = "enemyOf"
    allyOf = "allyOf"

    # Place → Nation
    placeToNation = "placeToNation"

    # {anything} → {anything}
    comparedTo = "comparedTo"
    contrastedWith = "contrastedWith"
    AliasOf = "AliasOf"


class BookCategoryName(Enum):
    # Tanach
    Torah = "Torah"
    Neviim = "Neviim"
    Ketuvim = "Ketuvim"
    # Babylonian Talmud
    Zeraim = "Zeraim"
    Moed = "Moed"
    Nashim = "Nashim"
    Nezikin = "Nezikin"
    Kodashim = "Kodashim"
    Tahorot = "Tahorot"


class SourceContentType(Enum):
    EN = 0
    HEB = 1
    EN_CLEAN = 2
