from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from BackEnd.DataObjects.SourceClasses import Source, SourceContentType
from BackEnd.DataObjects.SourceType import SourceType


class DBapiInterface(ABC):
    """
    An abstract base class defining the essential operations for a database API.
    """

    class CollectionName(str, Enum):
        BT = 'BT'  # Babylonian Talmud
        JT = 'JT'  # Jerusalem Talmud
        RM = 'RM'  # Rambam Mishne Torah
        TN = 'TN'  # Tanach
        MS = 'MS'  # Mishna
        FS = 'faiss_data'

    @staticmethod
    def is_valid_collection(name: str) -> bool:
        return name in DBapiInterface.CollectionName.__members__

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

    @abstractmethod
    def find_one(self, collection_name: str, key: str):
        pass

    @abstractmethod
    def find_one_source(self, collection_name: str, key: str) -> Source:
        pass

    # ----------------------------- Sources ----------------------------------

    def insert_source(self, result : Source, ref, start_index):
        en = result.content[SourceContentType.EN.value]
        heb = result.content[SourceContentType.HEB.value]

        data = {
            'key': result.get_key(),
            'content': [en, heb, ""],
            'summary': "",
            'filters': []
        }

        # Decide target collection based on source type
        if result.src_type == SourceType.BT:
            collection = self.CollectionName.BT.value
        elif result.src_type == SourceType.TN:
            collection = self.CollectionName.TN.value
        else:
            print(f"Unknown src_type '{result.src_type}' at index {start_index}")
            return

        # Check for existing document with same key
        existing = self.find_one(collection, data["key"])
        if existing:
            # Skip insert if key already exists
            # print(f" insert: key '{data['key']}' ")
            return
        else:
            print(f"inserting key '{data['key']}'")

        # Perform insert
        self.insert(collection, data)

    def update_by_key(self, collection_name: str, key: str, update: Dict[str, Any]) -> int:
        """
        Update a document in the collection using its unique key.

        Args:
            collection_name: Name of the collection.
            key: The unique key identifying the document.
            update: Dict of fields to update.

        Returns:
            Number of documents modified.
        """
        # Build query using the key
        query = {"key": key}

        # Call the existing update method
        return self.update(collection_name, query, update)

    def update_doc_field(
            self,
            doc: Dict[str, Any],
            collection_name: str,
            update_dict: Dict[str, Any],
            action_desc: str = "update"
    ) -> int:
        try:
            doc_key = doc.get('key')
            if not doc_key:
                print(f"[Error] Document missing 'key' field: {doc}")
                return 0

            modified_count: int = self.update_by_key(collection_name, doc_key, update_dict)
            # if modified_count == 0:
                # print(f"[Info] No document {action_desc} for key '{doc_key}' in collection '{collection_name}'")
            return modified_count
        except Exception as e:
            print(f"[Error] Failed to {action_desc} for key '{doc.get('key', 'unknown')}': {e}")
            return 0

    # ----------------------------- FAISS ------------------------------------
    @abstractmethod
    def save_faiss_index(self, index_bytes: bytes, metadata_bytes: bytes) -> None:
        """
        Save the FAISS index and metadata bytes to the database.
        """
        pass

    @abstractmethod
    def load_faiss_index(self) -> Optional[Tuple[bytes, bytes]]:
        """
        Load the FAISS index and metadata bytes from the database.
        Returns None if not found.
        """
        pass


