from typing import List

from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.NER import NER


class PassageToEntityNER:
    ref:str
    entities:List[Entity]
    ners:List[NER]