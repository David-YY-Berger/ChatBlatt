from backend.models.Enums import NumberCategory

# --- Global Constants ---
TRIBES_OF_ISRAEL = {
    "reuben",
    "simeon",
    "levi",
    "judah",
    "dan",
    "naphtali",
    "gad",
    "asher",
    "issachar",
    "zebulun",
    "joseph",
    "benjamin",
    "ephraim",
    "manasseh",
}

# Entity category names - used for validation and iteration
ENTITY_CATEGORIES = (
    "Person",
    "Place",
    "TribeOfIsrael",
    "Nation",
    "Symbol",
    "Number",
    "Animal",
    "Food",
    "Plant",
)

# Demonym to Nation name mapping (lowercase keys for matching)
# Includes nations from Tanach, Talmud, and Midrash
DEMONYM_TO_NATION = {
    # === Major Biblical Nations ===
    "aramean": "Aram",
    "arameans": "Aram",
    "syrian": "Syria",  # Aram often called Syria
    "syrians": "Syria",
    "egyptian": "Egypt",
    "egyptians": "Egypt",
    "moabite": "Moab",
    "moabites": "Moab",
    "ammonite": "Ammon",
    "ammonites": "Ammon",
    "edomite": "Edom",
    "edomites": "Edom",
    "philistine": "Philistia",
    "philistines": "Philistia",
    "assyrian": "Assyria",
    "assyrians": "Assyria",
    "babylonian": "Babylon",
    "babylonians": "Babylon",
    "chaldean": "Chaldea",  # Chaldeans ruled Babylon
    "chaldeans": "Chaldea",
    "persian": "Persia",
    "persians": "Persia",
    "median": "Media",
    "medians": "Media",
    "mede": "Media",
    "medes": "Media",
    "greek": "Greece",
    "greeks": "Greece",
    # === Canaanite Nations (Seven Nations) ===
    "canaanite": "Canaan",
    "canaanites": "Canaan",
    "hittite": "Hittites",
    "hittites": "Hittites",
    "amalekite": "Amalek",
    "amalekites": "Amalek",
    "midianite": "Midian",
    "midianites": "Midian",
    "ishmaelite": "Ishmael",
    "ishmaelites": "Ishmael",
    "kenite": "Kenites",
    "kenites": "Kenites",
    "jebusite": "Jebusites",
    "jebusites": "Jebusites",
    "girgashite": "Girgashites",
    "girgashites": "Girgashites",
    "hivite": "Hivites",
    "hivites": "Hivites",
    "perizzite": "Perizzites",
    "perizzites": "Perizzites",
}

# Symmetric relationships where (A, B) == (B, A)
SYMMETRIC_RELATIONSHIPS = (
    "spouseOf",
    "spokeWith",
    "disagreedWith",
    "EnemyOf",
    "AllyOf",
    "AliasOf",
    "comparedTo",
    "contrastedWith",
)

# Person -> Place relationships that supersede associatedWithPlace
# If a (person, place) pair exists in any of these, it should NOT appear in associatedWithPlace
PERSON_PLACE_SPECIFIC_RELATIONSHIPS = ("bornIn", "diedIn", "visited", "prayedAt")

max_len_summary: int = 10
min_len_summary: int = 4

# Build the allowed category literals from the enum
_NUMBER_CATEGORY_VALUES = [e.description for e in NumberCategory]

__all__ = [
    "TRIBES_OF_ISRAEL",
    "ENTITY_CATEGORIES",
    "DEMONYM_TO_NATION",
    "SYMMETRIC_RELATIONSHIPS",
    "PERSON_PLACE_SPECIFIC_RELATIONSHIPS",
    "max_len_summary",
    "min_len_summary",
    "_NUMBER_CATEGORY_VALUES",
]

