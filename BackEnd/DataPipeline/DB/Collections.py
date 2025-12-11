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

    # LMM
    LMM = Collection("LMM", "LMM")

    @classmethod
    def all(cls):
        return [
            cls.BT,
            cls.JT,
            cls.RM,
            cls.TN,
            cls.MS,

            cls.FS,

            cls.LMM,
        ]

    @classmethod
    def get_col_obj_from_str(cls, name: str) -> Collection | None:
        return next((c for c in cls.all() if c.name == name), None)