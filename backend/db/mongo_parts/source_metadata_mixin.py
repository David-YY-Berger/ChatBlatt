import logging
import re
from typing import Any, Dict, List, Optional

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields, DBOperators
from backend.models_db.Enums import PassageType, SourceType
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata

logger = logging.getLogger(__name__)


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

    def drop_all_source_metadata(self) -> int:
        """Delete all source metadata documents. Returns deleted count."""
        result = self.get_collection(CollectionObjs.SRC_METADATA).delete_many({})
        return result.deleted_count

    def get_source_metadata_by_key(self, key: str) -> Optional[SourceMetadata]:
        doc = self.get_collection(CollectionObjs.SRC_METADATA).find_one({DBFields.KEY: key})
        if doc is None:
            return None
        return self._doc_to_src_metadata(doc)

    def get_all_source_metadata(self) -> List[SourceMetadata]:
        docs = self.get_collection(CollectionObjs.SRC_METADATA).find({})
        return [self._doc_to_src_metadata(doc) for doc in docs]

    def get_source_metadata_by_entity_key(self, entity_key: str) -> List[SourceMetadata]:
        """
        Return all SourceMetadata documents whose entity_keys array contains
        the given entity_key. Used by the number-search feature to find every
        source passage that mentions a specific entity.
        """
        docs = self.get_collection(CollectionObjs.SRC_METADATA).find(
            {DBFields.ENTITY_KEYS: entity_key}
        )
        return [self._doc_to_src_metadata(doc) for doc in docs]

    def get_source_metadata_by_rel_key(self, rel_key: str) -> List[SourceMetadata]:
        """
        Return all SourceMetadata documents whose rel_keys array contains
        the given rel_key. Used to re-point/clean up source metadata when a
        relationship is remapped or removed (e.g. during entity merges).
        """
        docs = self.get_collection(CollectionObjs.SRC_METADATA).find(
            {DBFields.REL_KEYS: rel_key}
        )
        return [self._doc_to_src_metadata(doc) for doc in docs]

    def get_source_metadata_filtered(
        self,
        passage_types: Optional[List[PassageType]] = None,
        book_names: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None,
        rel_ids: Optional[List[str]] = None,
        src_types: Optional[List[SourceType]] = None,
    ) -> List[SourceMetadata]:
        """
        Fetch every SourceMetadata document matching the given filters in a
        single query. Each dimension is OR'd internally (matching any one of
        its selected values is enough) while the dimensions themselves are
        AND'd together. A dimension left empty/None is not filtered on at all.
        """
        conditions: List[Dict[str, Any]] = []

        if src_types:
            pattern = r"^(" + "|".join(re.escape(src_type.name) for src_type in src_types) + r")_"
            conditions.append({DBFields.KEY: {DBOperators.REGEX: pattern}})
        if passage_types:
            conditions.append({DBFields.PASSAGE_TYPES: {DBOperators.IN: [pt.value for pt in passage_types]}})
        if book_names:
            # Keys look like <TYPE>_<book>_<chapter>_<section>; match on the book segment.
            pattern = r"^[A-Z]{2}_(" + "|".join(re.escape(book) for book in book_names) + r")_"
            conditions.append({DBFields.KEY: {DBOperators.REGEX: pattern}})
        if entity_ids:
            conditions.append({DBFields.ENTITY_KEYS: {DBOperators.IN: list(entity_ids)}})
        if rel_ids:
            conditions.append({DBFields.REL_KEYS: {DBOperators.IN: list(rel_ids)}})

        query: Dict[str, Any] = {DBOperators.AND: conditions} if conditions else {}
        docs = self.get_collection(CollectionObjs.SRC_METADATA).find(query)
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

    @staticmethod
    def _parse_stored_passage_types(doc: Dict[str, Any]) -> List[PassageType]:
        """Skip stored values no longer in PassageType (e.g. legacy "Story", since
        split into STORY_TANACH/STORY_SAGES) so old docs don't crash reads."""
        valid = {pt.value: pt for pt in PassageType}
        stored = doc.get(DBFields.PASSAGE_TYPES, [])
        unknown = [v for v in stored if v not in valid]
        if unknown:
            logger.warning("Source %s has obsolete passage types %s; ignoring (re-run populator to reclassify)",
                           doc.get(DBFields.KEY), unknown)
        return [valid[v] for v in stored if v in valid]

    def _doc_to_src_metadata(self, doc: Dict[str, Any]) -> SourceMetadata:

        sm = SourceMetadata(doc.get(DBFields.KEY))
        sm.summary_en = doc.get(DBFields.SUMMARY_EN)
        sm.summary_heb = doc.get(DBFields.SUMMARY_HEB)
        sm.passage_types = self._parse_stored_passage_types(doc)
        sm.entity_keys = set(doc.get(DBFields.ENTITY_KEYS, []))
        sm.rel_keys = set(doc.get(DBFields.REL_KEYS, []))
        return sm
