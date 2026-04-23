from typing import Any, Dict, List, Optional

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.models.SourceClasses.SourceMetadata import SourceMetadata


class SourceMetadataMongoMixin:
    def get_collection(self, collection):
        raise NotImplementedError

    def is_src_metadata_exists(self, key: str) -> bool:
        return self.get_collection(CollectionObjs.SRC_METADATA).find_one({DBFields.KEY: key}) is not None

    def insert_source_metadata(self, src_metadata: SourceMetadata) -> str:
        data = self._src_metadata_to_doc(src_metadata)
        result = self.get_collection(CollectionObjs.SRC_METADATA).insert_one(data)
        return str(result.inserted_id)

    def update_source_metadata(self, src_metadata: SourceMetadata) -> int:
        data = self._src_metadata_to_doc(src_metadata)
        key = data.pop(DBFields.KEY)
        result = self.get_collection(CollectionObjs.SRC_METADATA).update_one(
            {DBFields.KEY: key},
            {DBOperators.SET: data},
        )
        return result.modified_count

    def get_source_metadata_by_key(self, key: str) -> Optional[SourceMetadata]:
        doc = self.get_collection(CollectionObjs.SRC_METADATA).find_one({DBFields.KEY: key})
        if doc is None:
            return None
        return self._doc_to_src_metadata(doc)

    def get_all_source_metadata(self) -> List[SourceMetadata]:
        docs = self.get_collection(CollectionObjs.SRC_METADATA).find({})
        return [self._doc_to_src_metadata(doc) for doc in docs]

    def _src_metadata_to_doc(self, src_metadata: SourceMetadata) -> Dict[str, Any]:
        return {
            DBFields.KEY: src_metadata.key,
            DBFields.SOURCE_TYPE: src_metadata.source_type.value,
            DBFields.SUMMARY_EN: src_metadata.summary_en,
            DBFields.SUMMARY_HEB: src_metadata.summary_heb,
            DBFields.PASSAGE_TYPES: [pt.value for pt in src_metadata.passage_types],
            DBFields.ENTITY_KEYS: list(src_metadata.entity_keys),
            DBFields.REL_KEYS: list(src_metadata.rel_keys),
        }

    def _doc_to_src_metadata(self, doc: Dict[str, Any]) -> SourceMetadata:
        from backend.models.Enums import PassageType, SourceType

        sm = SourceMetadata(source_type=SourceType(doc[DBFields.SOURCE_TYPE]))
        sm.key = doc[DBFields.KEY]
        sm.summary_en = doc.get(DBFields.SUMMARY_EN)
        sm.summary_heb = doc.get(DBFields.SUMMARY_HEB)
        sm.passage_types = [PassageType(pt) for pt in doc.get(DBFields.PASSAGE_TYPES, [])]
        sm.entity_keys = set(doc.get(DBFields.ENTITY_KEYS, []))
        sm.rel_keys = set(doc.get(DBFields.REL_KEYS, []))
        return sm


