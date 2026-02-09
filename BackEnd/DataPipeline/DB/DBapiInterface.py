from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.SourceClasses import SourceContent
from BackEnd.DataObjects.Enums import SourceType, SourceContentType
from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass
from BackEnd.DataObjects.SourceClasses.SourceMetadata import SourceMetadata
from BackEnd.DataPipeline.DB.Collections import CollectionObjs, Collection


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
    def execute_raw_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def execute_query_with_collection(self, query: Dict[str, Any], collection_name: str):
        pass

    @abstractmethod
    def insert(self, collection: CollectionObjs, data: Dict[str, Any]) -> str:
        """
        Insert data into a collection and return the inserted document ID.
        """
        pass

    @abstractmethod
    def update(self, collection: CollectionObjs, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update data in a collection based on a query.
        """
        pass

    @abstractmethod
    def delete_instance(self, collection: CollectionObjs, query: Dict[str, Any]) -> int:
        """
        Delete data from a collection based on a query.
        """
        pass

    @abstractmethod
    def delete_collection(self, collection: CollectionObjs) -> int:
        """
        Delete all documents from the given collection.
        Returns the number of documents deleted.
        """
        pass

    @abstractmethod
    def find_one(self, collection: Collection, key: str):
        pass

    def exists(self, collection: Collection, key: str) -> bool:
        return self.find_one(collection, key) is not None

    @abstractmethod
    def _find_one_source_content_by_col(self, collection: Collection, key: str) -> SourceContent:
        # allows for child classes to define impl
        pass

    def find_one_source_content(self, key:str) -> SourceContent:
        col_code = SourceClass.get_collection_name_from_key(key)
        if not col_code:
            raise KeyError
        col = CollectionObjs.get_col_obj_from_str(col_code)
        return self._find_one_source_content_by_col(col, key)

    @abstractmethod
    def get_all_src_contents_of_collection(self, collection: Collection) -> List[SourceContent]:
        pass

    # ----------------------------- Source Content ----------------------------------

    def insert_source_content(self, result : SourceContent, ref, start_index):
        en = result.content[SourceContentType.EN.value]
        heb = result.content[SourceContentType.HEB.value]

        data = {
            'key': result.get_key(),
            'content': [en, heb, ""],
        }

        # Decide target collection based on source type
        if result.get_src_type() == SourceType.BT:
            collection = CollectionObjs.BT.name
        elif result.get_src_type() == SourceType.TN:
            collection = CollectionObjs.TN.name
        else:
            print(f"Unknown src_type '{result.get_src_type()}' at index {start_index}")
            return

        # Check for existing document with same key
        if self.exists(collection, data["key"]):
            # Skip insert if key already exists
            # print(f" insert: key '{data['key']}' ")
            return
        else:
            print(f"inserting key '{data['key']}'")

        # Perform insert
        self.insert(collection, data)

    def update_by_key(self, collection: CollectionObjs, key: str, update: Dict[str, Any]) -> int:
        """
        Update a document in the collection using its unique key.

        Args:
            collection: Name of the collection.
            key: The unique key identifying the document.
            update: Dict of fields to update.

        Returns:
            Number of documents modified.
        """
        # Build query using the key
        query = {"key": key}

        # Call the existing update method
        return self.update(collection, query, update)

    def update_doc_field(self, doc: Dict[str, Any], collection: CollectionObjs, update_dict: Dict[str, Any], action_desc: str = "update") -> int:
        try:
            doc_key = doc.get('key')
            if not doc_key:
                print(f"[Error] Document missing 'key' field: {doc}")
                return 0

            modified_count: int = self.update_by_key(collection, doc_key, update_dict)
            # if modified_count == 0:
                # print(f"[Info] No document {action_desc} for key '{doc_key}' in collection '{collection}'")
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

    # ----------------------------- Source Metadata (Lmm) ------------------------------------
    @abstractmethod
    def is_src_metadata_exist(self, key: str) -> bool:
        # todo
        return True

    @abstractmethod
    def insert_source_metadata(self, src_metadata:SourceMetadata) -> str:
        # todo
        pass

    @abstractmethod
    def update_source_metadata(self, src_metadata:SourceMetadata) -> str:
        # todo
        pass

    def insert_or_update_source_metadata(self, src_metadata:SourceMetadata) -> str:
        if self.is_src_metadata_exist(src_metadata.key):
            return self.update_source_metadata(src_metadata)
        else:
            return self.insert_source_metadata(src_metadata)

# ----------------------------- Entity (Lmm) ------------------------------------
    @abstractmethod
    def is_entity_processed(self, key: str) -> bool:
        # todo
        return True

    @abstractmethod
    def get_all_entities(self) -> List[Entity]:
        pass
