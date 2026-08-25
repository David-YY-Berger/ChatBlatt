from dataclasses import dataclass

@dataclass(frozen=True)
class Collection:
    name: str
    db_name: str

class CollectionObjs:

    # DO NOT CHANGE THESE HARDCODED STRINGS they are written into the key's of objs in our db

    # Sources
    BT = Collection(name="BT", db_name="Sources")
    JT = Collection(name="JT", db_name="Sources")
    RM = Collection(name="RM", db_name="Sources")
    TN = Collection(name="TN", db_name="Sources")
    MS = Collection(name="MS", db_name="Sources")

    # FAISS
    FS = Collection(name="faiss_data", db_name="Faiss")

    # BM25 (keyword/lexical similarity index, complementing FAISS's semantic
    # similarity). Lives in the same "Faiss" search-index database, but its
    # own GridFS bucket, so it is populated/cleared fully independently of
    # the FAISS index.
    BM25 = Collection(name="bm25_data", db_name="Faiss")

    # Graphes
    SRC_METADATA = Collection(name="src_metadata", db_name="Graphs")
    ENTITIES = Collection(name="entities", db_name="Graphs")
    RELATIONS = Collection(name="relations", db_name="Graphs")

    @classmethod
    def all(cls):
        return [
            cls.BT,
            cls.JT,
            cls.RM,
            cls.TN,
            cls.MS,

            cls.FS,
            cls.BM25,

            cls.SRC_METADATA,
            cls.ENTITIES,
            cls.RELATIONS,
        ]

    @classmethod
    def get_col_obj_from_str(cls, name: str) -> Collection | None:
        return next((c for c in cls.all() if c.name == name), None)