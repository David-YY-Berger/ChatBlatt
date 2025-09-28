from typing import List


class NER:
    key:str
    term1: str # key of Entity
    term2: str # key of Entity
    appearances: List[str]

    # studiedFrom = (8, "StudiedFrom", "H")
    # personToPlace = (9, "PersonToPlace", "I")
    # personToNation = (10, "PersonToNation", "J")
    # comparedTo = (11, "ComparedTo", "K")
    # taughtMitzvah = (12, "TaughtMitzvah", "L")
    # performedMitzvah = (13, "PerformedMitzvah", "M")
