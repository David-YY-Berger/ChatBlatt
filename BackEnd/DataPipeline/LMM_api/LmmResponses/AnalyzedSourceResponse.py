from dataclasses import dataclass, field
from typing import List

from BackEnd.DataObjects.EntityObjects.EPerson import EPerson
from BackEnd.DataObjects.EntityObjects.EPlace import EPlace
from BackEnd.DataObjects.EntityObjects.ETribe import ETribe
from BackEnd.DataObjects.EntityObjects.ENation import ENation
from BackEnd.DataObjects.EntityObjects.ESymbol import ESymbol
from BackEnd.DataObjects.Enums import PassageType
from BackEnd.DataObjects.Rel import Rel


@dataclass
class AnalyzedSourceResponse:
    summary_en: str
    summary_heb: str
    e_passage_types: List[PassageType] = field(default_factory=list)

    # Entities
    e_persons: List[EPerson] = field(default_factory=list)
    e_places: List[EPlace] = field(default_factory=list)
    e_tribes: List[ETribe] = field(default_factory=list)
    e_nations: List[ENation] = field(default_factory=list)
    e_symbols: List[ESymbol] = field(default_factory=list)

    # Relationships
    rels: List[Rel] = field(default_factory=list)
