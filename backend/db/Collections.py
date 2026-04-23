from dataclasses import dataclass

@dataclass(frozen=True)
class Collection:
    name: str
    db_name: str

class CollectionObjs:

    # DO NOT CHANGE THESE HARDCODED STRINGS they are written into the key's of objs in our db

    # Sources
    BT = Collection("BT", "Sources")
    JT = Collection("JT", "Sources")
    RM = Collection("RM", "Sources")
    TN = Collection("TN", "Sources")
    MS = Collection("MS", "Sources")

    # FAISS
    FS = Collection("faiss_data", "Faiss")

    # LMM (Source Metadata)
    SRC_METADATA = Collection("src_metadata", "LMM")

    # Entities & Relations
    ENTITIES = Collection("entities", "EntitiesRels")
    RELATIONS = Collection("relations", "EntitiesRels")

    @classmethod
    def all(cls):
        return [
            cls.BT,
            cls.JT,
            cls.RM,
            cls.TN,
            cls.MS,

            cls.FS,

            cls.SRC_METADATA,
            cls.ENTITIES,
            cls.RELATIONS,
        ]

    @classmethod
    def get_col_obj_from_str(cls, name: str) -> Collection | None:
        return next((c for c in cls.all() if c.name == name), None)