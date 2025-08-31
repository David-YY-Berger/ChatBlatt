from enum import Enum


class CollectionName(str, Enum):

    #by chance, these are the same as Source Type..

    # Sources:
    BT = 'BT'  # Babylonian Talmud
    JT = 'JT'  # Jerusalem Talmud
    RM = 'RM'  # Rambam Mishne Torah
    TN = 'TN'  # Tanach
    MS = 'MS'  # Mishna

    # Filters:

    # FAISS:
    FS = 'faiss_data'

    # LMM:


    @staticmethod
    def is_valid_collection(name: str) -> bool:
            return name in CollectionName.__members__