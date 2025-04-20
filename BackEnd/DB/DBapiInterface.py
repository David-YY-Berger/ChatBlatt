from abc import ABC, abstractmethod
from typing import Any, Dict, List


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