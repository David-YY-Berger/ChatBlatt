# bs"d - lehagdil torah velahadir

from enum import Enum


class SourceType(Enum):
    BT = "Babylonian Talmud"
    JT = "Jerusalem Talmud"
    RM = "Rambam Mishne Torah"
    TN = "Tanach"
    MS = "Mishna"

class TimePeriod(Enum):
    """
    Each member carries (value, icon, color) so that UI badge styling lives
    directly on the enum — adding/renaming a member forces you to supply its
    style right here instead of relying on a separate hardcoded lookup that
    could silently fall out of sync.
    """
    Tanach = ("Tanach", "🕰️", "#b45309")
    Tanaim = ("Tanaim", "🕰️", "#15803d")
    Amoraim = ("Amoraim", "🕰️", "#1d4ed8")
    NoTimePeriod = ("No Time Period", "🕰️", "#6b7280")

    def __new__(cls, value: str, icon: str, color: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.icon = icon
        obj.color = color
        return obj

class SymbolType(Enum):
    """See TimePeriod for why (value, icon, color) are defined together."""
    Clothing = ("Clothing", "👕", "#db2777")
    HolyObject = ("Holy Object", "🕎", "#2563eb")
    BodyPart = ("Body Part", "🖐️", "#d97706")
    NotPhysical = ("Not Physical", "💭", "#6b7280")
    PartOfNature = ("Part of Nature", "🌿", "#059669")
    Weapon = ("Weapon", "⚔️", "#dc2626")
    Other = ("Other", "🔹", "#7c3aed")
    #     todo think of others!

    def __new__(cls, value: str, icon: str, color: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.icon = icon
        obj.color = color
        return obj

class PlaceType(Enum):
    """See TimePeriod for why (value, icon, color) are defined together."""
    City = ("City", "🏙️", "#2563eb")
    CountryOrRegion = ("Country or Region", "🗺️", "#059669")
    BuildingOrStructure = ("Building or Structure", "🏛️", "#7c3aed")
    BodyOfWater = ("Body of Water", "🌊", "#0891b2")
    Mountain = ("Mountain", "⛰️", "#78716c")
    Desert = ("Desert", "🏜️", "#d97706")
    NotPhysical = ("Not Physical", "💭", "#6b7280")
    Other = ("Other", "📍", "#db2777")
    #     todo think of others!

    def __new__(cls, value: str, icon: str, color: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.icon = icon
        obj.color = color
        return obj

class RoleType(Enum):
    """See TimePeriod for why (value, icon, color) are defined together."""
    Prophet = ("Prophet", "📜", "#7c3aed")
    King = ("King", "👑", "#b45309")
    Judge = ("Judge", "⚖️", "#0f766e")
    Kohen = ("Kohen", "🕎", "#1d4ed8")
    Tanna = ("Tanna", "📖", "#be185d")
    Amora = ("Amora", "📚", "#4338ca")

    def __new__(cls, value: str, icon: str, color: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.icon = icon
        obj.color = color
        return obj

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
