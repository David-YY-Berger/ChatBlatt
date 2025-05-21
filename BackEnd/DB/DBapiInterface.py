from abc import ABC, abstractmethod
from typing import Any, Dict, List

from BackEnd.Objects import SourceClasses
from BackEnd.Objects.SourceClasses import Source


class DBapiInterface(ABC):
    """
    An abstract base class defining the essential operations for a database API.
    """

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
    def insert(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Insert data into a collection and return the inserted document ID.
        """
        pass

    def insert_source(self, result : Source, ref, start_index):
        if result.src_type == SourceClasses.SourceType.BT:
            data = {'key': result.get_key(), 'content': result.content[SourceClasses.SourceContentType.EN.value] }
            self.insert("en-sources", data)
            pass

        elif result.src_type == SourceClasses.SourceType.TN:
            # handle type2
            pass

        else:
            # optional fallbacka
            print(f"Unknown src_type '{result.src_type}' at index {start_index}")

    @abstractmethod
    def update(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update data in a collection based on a query.
        """
        pass

    @abstractmethod
    def delete(self, collection: str, query: Dict[str, Any]) -> int:
        """
        Delete data from a collection based on a query.
        """
        pass

    @abstractmethod
    def delete_all(self, collection: str) -> int:
        """
        Delete all documents from the given collection.
        Returns the number of documents deleted.
        """
        pass