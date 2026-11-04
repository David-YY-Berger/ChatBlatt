# bs"d
"""
EntityMerger - key-based merge of duplicate entities (shared by DBPopulateMergeEntities [CSV]
and DBApplyMergeDecisions [review files]). See control_docs/pipeline/merge_entities.md.

merge_into_target(target, duplicates, final_name) folds each duplicate into the target ONE AT A
TIME: fold fields into target + persist, re-point every Rel and SourceMetadata reference from the
duplicate's key to the target's, then delete the duplicate. A duplicate is fully retired before
the next starts, so an interrupted run never leaves a half-merged entity (the remaining duplicate
is still a valid entity and can simply be merged on the next run).
"""

from enum import Enum
from typing import List, Optional

from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.EntityObjects.ENumber import ENumber
from backend.models_db.Rel import Rel

# Fields with special-cased merge logic in _fold_fields_into_target; every other persisted field is
# merged generically via reflection.
_SPECIAL_CASED_FIELDS = {
    "key", "entityType", "display_en_name", "display_heb_name",
    "all_en_names", "all_heb_names", "alias_keys", "contexts",
}


def _normalize_for_dedupe(item):
    if isinstance(item, str):
        return item.lower()
    if isinstance(item, Enum):
        return item.value
    return item


def merge_lists(*lists) -> list:
    """Union lists, de-duplicating (case/enum-insensitively), preserving first-seen order and casing."""
    seen = set()
    result = []
    for lst in lists:
        for item in (lst or []):
            if item is None or item == "":
                continue
            norm = _normalize_for_dedupe(item)
            if norm not in seen:
                seen.add(norm)
                result.append(item)
    return result


class EntityMerger:
    def __init__(self, db_api):
        self.db_api = db_api

    def choose_target(self, entities: List[Entity], final_name: str) -> Entity:
        """Target = entity already named `final_name`; otherwise the one with the most rels; ties by key."""
        wanted = final_name.strip().lower()
        named = [e for e in entities if e.display_en_name.strip().lower() == wanted]
        pool = named or entities
        ranked = sorted(pool, key=lambda e: (-len(self.db_api.get_rels_for_entity(e.key)), e.key))
        return ranked[0]

    def merge_into_target(self, target: Entity, duplicates: List[Entity], final_name: str) -> None:
        canonical = final_name.strip().lower()
        for dup in duplicates:
            if dup.key == target.key:
                continue
            self._merge_one(target, dup, canonical, final_name.strip())

    def _merge_one(self, target: Entity, dup: Entity, canonical_name: str, original_name: str) -> None:
        self.fold_fields_into_target(target, dup, canonical_name, original_name)
        self.db_api.update_entity(target)
        self._repoint_rels(target.key, dup.key)
        self._repoint_source_metadata_entity_key(target.key, dup.key)
        self.db_api.delete_entity_by_key(dup.key)

    @staticmethod
    def fold_fields_into_target(target: Entity, dup: Entity, canonical_name: str, original_name: str) -> None:
        """
        Mutate `target` to absorb `dup`: display_en_name := canonical_name; display_heb_name filled
        if empty; all_en_names/all_heb_names/alias_keys unioned (the duplicate's display name, the
        final name, and the duplicate's key are kept as aliases so old references stay traceable);
        every other persisted field merged generically (lists unioned, bools OR'd, scalars fill-if-empty -
        the target's value wins on conflict).
        """
        target.display_en_name = canonical_name
        if not target.display_heb_name and dup.display_heb_name:
            target.display_heb_name = dup.display_heb_name

        target.all_en_names = merge_lists(
            target.all_en_names, dup.all_en_names, [dup.display_en_name, original_name]
        )
        target.all_heb_names = merge_lists(target.all_heb_names, dup.all_heb_names)
        target.alias_keys = merge_lists(target.alias_keys, dup.alias_keys, [dup.key])
        if isinstance(target, ENumber) and isinstance(dup, ENumber):
            target.merge_contexts(dup.contexts)

        for field_name in type(target).get_db_field_names():
            if field_name in _SPECIAL_CASED_FIELDS:
                continue
            target_value = getattr(target, field_name, None)
            dup_value = getattr(dup, field_name, None)
            if isinstance(target_value, list):
                setattr(target, field_name, merge_lists(target_value, dup_value))
            elif isinstance(target_value, bool):
                setattr(target, field_name, bool(target_value) or bool(dup_value))
            elif not target_value and dup_value:
                setattr(target, field_name, dup_value)

    def _repoint_rels(self, target_key: str, dup_key: str) -> None:
        """
        Re-point every Rel referencing dup_key to target_key. A rel that would become a self-loop
        is dropped; otherwise try_insert_rel re-points it, de-duplicating against an identical
        existing rel (NOTE: the reversed pair of a symmetric rel is not detected as a duplicate).
        SourceMetadata.rel_keys follow the rel to its new (or de-duplicated) key; the old rel is deleted.
        """
        for rel in self.db_api.get_rels_for_entity(dup_key):
            new_term1 = target_key if rel.term1 == dup_key else rel.term1
            new_term2 = target_key if rel.term2 == dup_key else rel.term2

            new_key: Optional[str] = None
            if new_term1 != new_term2:
                new_key = self.db_api.try_insert_rel(Rel.create(rel_type=rel.rel_type, term1=new_term1, term2=new_term2))

            self._repoint_source_metadata_rel_key(rel.key, new_key)
            self.db_api.delete_rel_by_key(rel.key)

    def _repoint_source_metadata_entity_key(self, target_key: str, dup_key: str) -> None:
        for sm in self.db_api.get_source_metadata_by_entity_key(dup_key):
            sm.entity_keys.discard(dup_key)
            sm.entity_keys.add(target_key)
            self.db_api.update_source_metadata(sm)

    def _repoint_source_metadata_rel_key(self, old_rel_key: str, new_rel_key: Optional[str]) -> None:
        for sm in self.db_api.get_source_metadata_by_rel_key(old_rel_key):
            sm.rel_keys.discard(old_rel_key)
            if new_rel_key:
                sm.rel_keys.add(new_rel_key)
            self.db_api.update_source_metadata(sm)
