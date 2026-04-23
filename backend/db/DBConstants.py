# bs"d
"""
Database field name constants.
Centralizes all hardcoded field names used in MongoDB operations.
"""


class DBFields:
    """MongoDB document field names."""

    # Common fields
    KEY = "key"

    # Entity fields
    ENTITY_TYPE = "entityType"
    DISPLAY_EN_NAME = "display_en_name"
    DISPLAY_HEB_NAME = "display_heb_name"
    ALL_EN_NAMES = "all_en_names"
    ALL_HEB_NAMES = "all_heb_names"

    # Relationship fields
    REL_TYPE = "rel_type"
    TERM1 = "term1"
    TERM2 = "term2"

    # Source Metadata fields
    SOURCE_TYPE = "source_type"
    SUMMARY_EN = "summary_en"
    SUMMARY_HEB = "summary_heb"
    PASSAGE_TYPES = "passage_types"
    ENTITY_KEYS = "entity_keys"
    REL_KEYS = "rel_keys"

    # FAISS fields
    FAISS_INDEX = "faiss_index"
    METADATA = "metadata"


class DBOperators:
    """MongoDB query operators."""

    SET = "$set"
    OR = "$or"
    AND = "$and"
    IN = "$in"
    REGEX = "$regex"
    OPTIONS = "$options"

    # Regex options
    CASE_INSENSITIVE = "i"

