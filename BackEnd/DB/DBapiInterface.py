from abc import ABC, abstractmethod
from typing import Any, Dict, List

from BackEnd.Objects import SourceClasses
from BackEnd.Objects.SourceClasses import Source


class DBapiInterface(ABC):
    """
    An abstract base class defining the essential operations for a database API.
    """

    # Collection name constants
    BT = 'BT'  # Babylonian Talmud
    JT = 'JT'  # Jerusalem Talmud
    RM = 'RM'  # Rambam Mishne Torah
    TN = 'TN'  # Tanach
    MS = 'MS'  # Mishna

    @abstractmethod
    def connect(self, connection_string: str) -> None:
        """
        Establish a connection to the database.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close the connection to the database.
        """
        pass

    @abstractmethod
    def execute_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query on the database and return the results.
        """
        pass

    @abstractmethod
    def insert(self, collection_name: str, data: Dict[str, Any]) -> str:
        """
        Insert data into a collection and return the inserted document ID.
        """
        pass

    def insert_source(self, result : Source, start_index):
        if result.src_type == SourceClasses.SourceType.BT:
            data = {'key': result.get_key(), 'content': result.content[SourceClasses.SourceContentType.EN.value] }
            self.insert(self.BT, data)
            pass

        elif result.src_type == SourceClasses.SourceType.TN:
            # todo must add to DB
            pass

        else:
            # optional fallback
            print(f"Unknown src_type '{result.src_type}' at index {start_index}")

    @abstractmethod
    def update(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update data in a collection based on a query.
        """
        pass

    @abstractmethod
    def delete_instance(self, collection_name: str, query: Dict[str, Any]) -> int:
        """
        Delete data from a collection based on a query.
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> int:
        """
        Delete all documents from the given collection.
        Returns the number of documents deleted.
        """
        pass