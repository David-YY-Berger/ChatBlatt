# bs"d
"""
Shared test fixtures: a fake DBapiMongoDB that uses mongomock collections
so we never touch real data.
"""
from unittest.mock import MagicMock
from collections import defaultdict
from copy import deepcopy
from bson import ObjectId

from backend.db.Collections import Collection


TEST_SOURCE_KEY = "TN_Joshua_0_99:1–2"


# ---------------------------------------------------------------------------
# Lightweight in-memory Mongo collection that behaves like pymongo.Collection
# ---------------------------------------------------------------------------
class FakeCollection:
    """Minimal pymongo.Collection stand-in backed by a plain list."""

    def __init__(self):
        self._docs = []

    # ---- helpers ----
    def _matches(self, doc, filt):
        """Very small query evaluator – supports top-level eq, $in, $or, $and, $regex."""
        for key, val in filt.items():
            if key == "$or":
                if not any(self._matches(doc, sub) for sub in val):
                    return False
            elif key == "$and":
                if not all(self._matches(doc, sub) for sub in val):
                    return False
            elif isinstance(val, dict):
                if "$in" in val:
                    if doc.get(key) not in val["$in"]:
                        return False
                if "$regex" in val:
                    import re
                    flags = re.IGNORECASE if val.get("$options", "") == "i" else 0
                    field_val = doc.get(key)
                    if isinstance(field_val, list):
                        if not any(re.search(val["$regex"], item, flags) for item in field_val if isinstance(item, str)):
                            return False
                    elif not isinstance(field_val, str) or not re.search(val["$regex"], field_val, flags):
                        return False
            else:
                if doc.get(key) != val:
                    return False
        return True

    # ---- pymongo-like API ----
    def insert_one(self, doc):
        doc = deepcopy(doc)
        doc.setdefault("_id", ObjectId())
        self._docs.append(doc)
        return MagicMock(inserted_id=doc["_id"])

    def insert_many(self, docs):
        ids = []
        for d in docs:
            r = self.insert_one(d)
            ids.append(r.inserted_id)
        return MagicMock(inserted_ids=ids)

    def find_one(self, filt=None):
        filt = filt or {}
        for d in self._docs:
            if self._matches(d, filt):
                return deepcopy(d)
        return None

    def find(self, filt=None):
        filt = filt or {}
        return [deepcopy(d) for d in self._docs if self._matches(d, filt)]

    def update_one(self, filt, update, upsert=False):
        for d in self._docs:
            if self._matches(d, filt):
                if "$set" in update:
                    d.update(update["$set"])
                return MagicMock(modified_count=1, upserted_count=0, upserted_id=None)
        if upsert:
            new_doc = {**filt}
            if "$set" in update:
                new_doc.update(update["$set"])
            new_doc.setdefault("_id", ObjectId())
            self._docs.append(new_doc)
            return MagicMock(modified_count=0, upserted_count=1, upserted_id=new_doc["_id"])
        return MagicMock(modified_count=0, upserted_count=0, upserted_id=None)

    def update_many(self, filt, update):
        count = 0
        for d in self._docs:
            if self._matches(d, filt):
                if "$set" in update:
                    d.update(update["$set"])
                count += 1
        return MagicMock(modified_count=count)

    def delete_many(self, filt):
        before = len(self._docs)
        self._docs = [d for d in self._docs if not self._matches(d, filt)]
        return MagicMock(deleted_count=before - len(self._docs))

    def bulk_write(self, operations):
        upserted = 0
        modified = 0
        for op in operations:
            # UpdateOne objects from pymongo
            filt = op._filter
            upd = op._doc
            is_upsert = op._upsert
            result = self.update_one(filt, upd, upsert=is_upsert)
            upserted += result.upserted_count
            modified += result.modified_count
        return MagicMock(upserted_count=upserted, modified_count=modified)

    def count_documents(self, filt=None):
        return len(self.find(filt))


# ---------------------------------------------------------------------------
# Fake DB that plugs into DBapiMongoDB without a real connection
# ---------------------------------------------------------------------------
class FakeDBapi:
    """
    Creates a DBapiMongoDB-like object that uses FakeCollections.
    Usage:
        db = FakeDBapi.create()
    """

    @staticmethod
    def create():
        """Return a DBapiMongoDB whose get_collection returns FakeCollections."""
        # We import here so the singleton decorator doesn't block us;
        # we'll just build the mixins manually via the concrete class.
        from backend.db.mongo_parts.entity_mixin import EntityMongoMixin
        from backend.db.mongo_parts.relationship_mixin import RelationshipMongoMixin
        from backend.db.mongo_parts.source_content_mixin import SourceContentMongoMixin
        from backend.db.mongo_parts.source_metadata_mixin import SourceMetadataMongoMixin
        from backend.db.mongo_parts.faiss_mixin import FaissMongoMixin

        collections = defaultdict(FakeCollection)

        class _TestDB(
            SourceContentMongoMixin,
            FaissMongoMixin,
            EntityMongoMixin,
            RelationshipMongoMixin,
            SourceMetadataMongoMixin,
        ):
            def __init__(self):
                self.client = True  # truthy so source_content_mixin checks pass

            def get_collection(self, collection: Collection):
                return collections[(collection.db_name, collection.name)]

        return _TestDB()


