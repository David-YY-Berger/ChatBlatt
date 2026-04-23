from typing import Any, Dict, List

from backend.db.Collections import Collection
from backend.models.SourceClasses.SourceContent import SourceContent


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
        if not self.client:
            raise Exception("Database connection is not established.")

        docs = self.get_collection(collection).find({})
        return [
            SourceContent(key=doc["key"], content=doc["content"])
            for doc in docs
            if "key" in doc and "content" in doc
        ]


