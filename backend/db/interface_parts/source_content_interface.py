from abc import ABC, abstractmethod
from typing import Any, Dict, List

from backend.db.Collections import CollectionObjs, Collection
from backend.db.DBConstants import DBFields
from backend.models.Enums import SourceType, SourceContentType
from backend.models.SourceClasses.SourceClass import SourceClass
from backend.models.SourceClasses.SourceContent import SourceContent


class SourceContentInterfaceMixin(ABC):
    @abstractmethod
    def insert(self, collection: Collection, data: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def update(self, collection: Collection, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    def find_one(self, collection: Collection, key: str):
        pass

    def exists(self, collection: Collection, key: str) -> bool:
        return self.find_one(collection, key) is not None

    @abstractmethod
    def _find_one_source_content_by_col(self, collection: Collection, key: str) -> SourceContent:
        pass

    def find_one_source_content(self, key: str) -> SourceContent:
        col_code = SourceClass.get_collection_name_from_key(key)
        if not col_code:
            raise KeyError
        col = CollectionObjs.get_col_obj_from_str(col_code)
        return self._find_one_source_content_by_col(col, key)

    @abstractmethod
    def get_all_src_contents_of_collection(self, collection: Collection) -> List[SourceContent]:
        pass

    def insert_source_content(self, result: SourceContent, ref, start_index):
        en = result.content[SourceContentType.EN.value]
        heb = result.content[SourceContentType.HEB.value]

        data = {
            DBFields.KEY: result.get_key(),
            "content": [en, heb, ""],
        }

        # Decide target collection based on source type
        if result.get_src_type() == SourceType.BT:
            collection = CollectionObjs.BT
        elif result.get_src_type() == SourceType.TN:
            collection = CollectionObjs.TN
        else:
            print(f"Unknown src_type '{result.get_src_type()}' at index {start_index}")
            return

        # Check for existing document with same key
        if self.exists(collection, data[DBFields.KEY]):
            return
        else:
            print(f"inserting key '{data[DBFields.KEY]}'")

        self.insert(collection, data)

    def update_by_key(self, collection: CollectionObjs, key: str, update: Dict[str, Any]) -> int:
        query = {DBFields.KEY: key}
        return self.update(collection, query, update)

    def update_doc_field(
        self,
        doc: Dict[str, Any],
        collection: CollectionObjs,
        update_dict: Dict[str, Any],
        action_desc: str = "update",
    ) -> int:
        try:
            doc_key = doc.get(DBFields.KEY)
            if not doc_key:
                print(f"[Error] Document missing 'key' field: {doc}")
                return 0

            return self.update_by_key(collection, doc_key, update_dict)
        except Exception as e:
            print(f"[Error] Failed to {action_desc} for key '{doc.get(DBFields.KEY, 'unknown')}': {e}")
            return 0



