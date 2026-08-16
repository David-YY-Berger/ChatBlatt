# bs"d - lehagdil torah velahadir

from enum import Enum


class Color:
    """
    Named color palette (hex) shared by all :class:`ColoredEnum` subclasses.
    Enum members reference these constants (e.g. ``Color.BLUE``) instead of
    hardcoding raw hex strings, so the palette stays curated and consistent
    across the app.
    """
    RED = "#dc2626"
    ORANGE = "#d97706"
    AMBER = "#b45309"
    GOLD = "#ca8a04"
    GREEN = "#059669"
    EMERALD = "#15803d"
    TEAL = "#0f766e"
    CYAN = "#0891b2"
    BLUE = "#2563eb"
    ROYAL_BLUE = "#1d4ed8"
    INDIGO = "#4338ca"
    VIOLET = "#7c3aed"
    PURPLE = "#9333ea"
    PINK = "#db2777"
    ROSE = "#be185d"
    BROWN = "#78716c"
    GRAY = "#6b7280"


class ColoredEnum(Enum):
    """
    Base class for enums that carry (value, icon, color) so that UI badge
    styling lives directly on the enum member — adding/renaming a member
    forces you to supply its style right here instead of relying on a
    separate hardcoded lookup that could silently fall out of sync.
    Colors should reference the named constants on :class:`Color`.
    """
    def __new__(cls, value: str, icon: str, color: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.icon = icon
        obj.color = color
        return obj


class SourceType(Enum):
    BT = "Babylonian Talmud"
    JT = "Jerusalem Talmud"
    RM = "Rambam Mishne Torah"
    TN = "Tanach"
    MS = "Mishna"

class TimePeriod(ColoredEnum):
    """See ColoredEnum for why (value, icon, color) are defined together."""
    Tanach = ("Tanach", "🕰️", Color.AMBER)
    Tanaim = ("Tanaim", "🕰️", Color.EMERALD)
    Amoraim = ("Amoraim", "🕰️", Color.ROYAL_BLUE)
    NoTimePeriod = ("No Time Period", "🕰️", Color.GRAY)

class SymbolType(ColoredEnum):
    """See ColoredEnum for why (value, icon, color) are defined together."""
    Clothing = ("Clothing", "👕", Color.PINK)
    HolyObject = ("Holy Object", "🕎", Color.BLUE)
    BodyPart = ("Body Part", "🖐️", Color.ORANGE)
    NotPhysical = ("Not Physical", "💭", Color.GRAY)
    PartOfNature = ("Part of Nature", "🌿", Color.GREEN)
    Weapon = ("Weapon", "⚔️", Color.RED)
    Other = ("Other", "🔹", Color.VIOLET)
    #     todo think of others!

class PlaceType(ColoredEnum):
    """See ColoredEnum for why (value, icon, color) are defined together."""
    City = ("City", "🏙️", Color.BLUE)
    CountryOrRegion = ("Country or Region", "🗺️", Color.GREEN)
    BuildingOrStructure = ("Building or Structure", "🏛️", Color.VIOLET)
    BodyOfWater = ("Body of Water", "🌊", Color.CYAN)
    Mountain = ("Mountain", "⛰️", Color.BROWN)
    Desert = ("Desert", "🏜️", Color.ORANGE)
    NotPhysical = ("Not Physical", "💭", Color.GRAY)
    Other = ("Other", "📍", Color.PINK)
    #     todo think of others!

class RoleType(ColoredEnum):
    """See ColoredEnum for why (value, icon, color) are defined together."""
    Prophet = ("Prophet", "📜", Color.VIOLET)
    King = ("King", "👑", Color.AMBER)
    Judge = ("Judge", "⚖️", Color.TEAL)
    Kohen = ("Kohen", "🕎", Color.ROYAL_BLUE)
    Tanna = ("Tanna", "📖", Color.ROSE)
    Amora = ("Amora", "📚", Color.INDIGO)

class NumberCategory(Enum):
    """
    Each member carries (value, ordinal) so the intended left-to-right
    display order is explicit and stored on the enum itself — reordering
    the UI means editing ``ordinal`` here instead of maintaining a separate
    order list elsewhere that could fall out of sync.
    """
    Time = ("Time", 1)                 # Duration, age, dates, periods
    People = ("People", 2)             # Counts of persons, armies, tribes
    Measurement = ("Measurement", 3)   # Distance, weight, volume, area
    Sacrifice = ("Sacrifice", 4)       # Offerings: animals, flour, oil, incense
    Money = ("Money", 5)               # Currency, payment, value
    Misc = ("Misc", 6)                 # Anything not covered above

    def __new__(cls, value: str, ordinal: int):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.ordinal = ordinal
        return obj

class PassageType(ColoredEnum):
    """See ColoredEnum for why (value, icon, color) are defined together.
    No relationship to TimePeriod — this describes the nature of a passage
    (law, story, etc.), not when it was authored."""
    LAW = ("Law", "⚖️", Color.BLUE)
    STORY = ("Story", "📖", Color.AMBER)
    PHILOSOPHIC = ("Philosophic", "💭", Color.VIOLET)
    GENEALOGY = ("Genealogy", "🌳", Color.EMERALD)
    PROPHECY = ("Prophecy", "🔮", Color.ROSE)

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
