from enum import Enum
from typing import Dict, List

from BackEnd.DataObjects.SourceType import SourceType


class FilterNames(Enum):
    PEOPLE = "People"
    PLACES = "Places"
    TYPE_OF_PASSAGE = "Type Of Passage"


class Filters:
    def __init__(self, src_type: SourceType):
        # Initialize the filter map depending on src_type
        self.f_map: Dict[str, List[int]] = {}

        # Only BT includes TypeOfTalmudPassage
        if src_type == SourceType.BT or src_type == SourceType.TN:
            self.f_map[FilterNames.TYPE_OF_PASSAGE.value] = []
            self.f_map[FilterNames.PEOPLE.value] = []
            self.f_map[FilterNames.PLACES.value] = []

    def to_dict(self):
        return self.f_map


