import re
from typing import Any, Dict, List

from backend.db.Collections import Collection, CollectionObjs
from backend.db.data_names.Books import Book
from backend.models_db.SourceClasses.SourceContent import SourceContent


class SourceContentMongoMixin:
    client: Any

    def get_collection(self, collection: Collection):
        raise NotImplementedError

    def find_one(self, collection: Collection, key: str) -> Dict[str, Any] | None:
        if not self.client:
            raise Exception("Database connection is not established.")
        return self.get_collection(collection).find_one({"key": key})

    def _find_one_source_content_by_col(self, collection: Collection, key: str) -> SourceContent:
        db_object = self.find_one(collection, key)
        if db_object is None:
            raise Exception(f"Document with key '{key}' not found in collection {collection.name}.")

        return SourceContent(
            key=db_object["key"],
            content=db_object["content"],
        )

    def get_all_src_contents_of_collection(self, collection: Collection) -> List[SourceContent]:
        """Get all SourceContent documents from a given collection."""
        if not self.client:
            raise Exception("Database connection is not established.")

        docs = self.get_collection(collection).find(
            {"key": {"$exists": True}, "content": {"$exists": True}},
            {"key": 1, "content": 1, "_id": 0}
        )
        return [
            SourceContent(key=doc["key"], content=doc["content"])
            for doc in docs
        ]

    def get_all_src_contents_by_book(self, book: Book) -> List[SourceContent]:
        """Get all SourceContent documents that belong to a specific book.

        The key format is: '<SOURCE_TYPE>_<BOOK_NAME>_0_<ref>'
        e.g. 'TN_Genesis_0_6:14-25' or 'BT_Sanhedrin_0_96b:2-9'
        We filter by regex on the key field matching the book's database_name.
        """
        if not self.client:
            raise Exception("Database connection is not established.")

        collection = CollectionObjs.get_col_obj_from_str(book.source_type.name)
        if collection is None:
            raise Exception(f"No collection found for source type '{book.source_type.name}'.")

        # Key pattern: <SOURCE_TYPE>_<BookDatabaseName>_
        key_prefix = f"{book.source_type.name}_{book.database_name}_"
        query = {
            "key": {"$regex": f"^{re.escape(key_prefix)}"},
            "content": {"$exists": True}
        }

        docs = self.get_collection(collection).find(query, {"key": 1, "content": 1, "_id": 0})
        results = [
            SourceContent(key=doc["key"], content=doc["content"])
            for doc in docs
        ]
        results.sort()  # Uses SourceClass.__lt__ (book order, then section)
        return results
