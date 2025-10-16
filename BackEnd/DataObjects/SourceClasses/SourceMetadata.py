from dataclasses import dataclass, field
from typing import Any, List, Optional

from BackEnd.DataObjects.Enums import SourceType
from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass


@dataclass
class SourceMetadata(SourceClass):
    book_name: str
    source_type: SourceType
    entities: List[str]
    rels: List[str]
    summary: List[str]

    def __init__(
        self,
        key: str,
        book_name: str,
        source_type: SourceType,
        entities: Optional[List[str]] = None,
        rels: Optional[List[str]] = None,
        summary: Optional[List[str]] = None
    ):
        super().__init__(key)
        self._book_name = book_name
        self._source_type = source_type
        self._entities = entities or []
        self._rels = rels or []
        self._summary = summary or []

    @property
    def book_name(self):
        return self._book_name

    @book_name.setter
    def book_name(self, value):
        self._book_name = value

    @property
    def source_type(self):
        return self._source_type

    @source_type.setter
    def source_type(self, value):
        self._source_type = value

    @property
    def entities(self):
        return self._entities

    @entities.setter
    def entities(self, value):
        self._entities = value or []

    @property
    def rels(self):
        return self._rels

    @rels.setter
    def rels(self, value):
        self._rels = value or []

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, value):
        self._summary = value or []
