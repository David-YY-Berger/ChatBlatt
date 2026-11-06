"""Remove existing folio/page Numbers and their graph references from the real DB.

Run from the project root with ``python -m
backend_pipeline.data_pipeline.one_time_scripts.clean_folio_page_numbers``.
This is a dry run unless --apply is passed. Stop graph population first and
back up the Graphs database before applying. Each Number is cleaned in its
own transaction, so an interrupted run can be safely repeated.
"""
import argparse

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields
from backend.db.DBFactory import DBFactory
from backend.models_db.Enums import EntityType


UNITS_TO_CLEAN = frozenset({"folio", "page"})


def _is_target(doc: dict) -> bool:
    unit = doc.get("en_unit")
    return (
        doc.get(DBFields.ENTITY_TYPE) == EntityType.ENumber.value
        and isinstance(unit, str)
        and unit.strip().lower() in UNITS_TO_CLEAN
    )


def _cleanup_one(db, entity_id, apply: bool) -> tuple:
    entities = db.get_collection(CollectionObjs.ENTITIES)
    relations = db.get_collection(CollectionObjs.RELATIONS)
    metadata = db.get_collection(CollectionObjs.SRC_METADATA)
    entity = entities.find_one({"_id": entity_id})
    if entity is None or not _is_target(entity):
        raise ValueError(f"Number {entity_id} disappeared or changed during cleanup")
    key = entity.get(DBFields.KEY)
    if not isinstance(key, str) or not key:
        raise ValueError(f"Number {entity_id} has no usable key")

    rel_query = {"$or": [{DBFields.TERM1: key}, {DBFields.TERM2: key}]}
    rels = list(relations.find(rel_query, {"_id": 1, DBFields.KEY: 1}))
    rel_keys = []
    for rel in rels:
        rel_key = rel.get(DBFields.KEY)
        if not isinstance(rel_key, str) or not rel_key:
            raise ValueError(f"Relationship {rel['_id']} has no usable key")
        rel_keys.append(rel_key)

    entity_meta_query = {DBFields.ENTITY_KEYS: {"$in": [key]}}
    rel_meta_query = {DBFields.REL_KEYS: {"$in": rel_keys}}
    entity_sources = metadata.count_documents(entity_meta_query)
    rel_sources = metadata.count_documents(rel_meta_query) if rel_keys else 0
    if apply:
        metadata.update_many(entity_meta_query, {"$pull": {DBFields.ENTITY_KEYS: key}})
        if rel_keys:
            metadata.update_many(rel_meta_query, {"$pull": {DBFields.REL_KEYS: {"$in": rel_keys}}})
        relations.delete_many(rel_query)
        deleted = entities.delete_one({"_id": entity_id})
        if deleted.deleted_count != 1:
            raise RuntimeError(f"Failed to delete Number {entity_id}")
    return len(rels), entity_sources, rel_sources


def clean(db, apply: bool) -> None:
    entities = db.get_collection(CollectionObjs.ENTITIES)
    candidates = [
        doc for doc in entities.find(
            {DBFields.ENTITY_TYPE: EntityType.ENumber.value},
            {"_id": 1, DBFields.KEY: 1, DBFields.ENTITY_TYPE: 1,
             DBFields.DISPLAY_EN_NAME: 1, "en_unit": 1},
        )
        if _is_target(doc)
    ]
    totals = [0, 0, 0]
    for doc in candidates:
        if apply:
            counts = db.run_in_transaction(lambda: _cleanup_one(db, doc["_id"], True))
        else:
            counts = _cleanup_one(db, doc["_id"], False)
        totals = [total + count for total, count in zip(totals, counts)]
        print(f"{'Removed' if apply else 'Would remove'} {doc.get(DBFields.KEY)}: "
              f"{doc.get(DBFields.DISPLAY_EN_NAME)} {doc['en_unit']} "
              f"({counts[0]} relationships, {counts[1]} source documents with the entity, "
              f"{counts[2]} source documents with its relationships)")
    print(f"{len(candidates)} Numbers; summed per-Number counts: {totals[0]} relationships, "
          f"{totals[1]} source documents with entities, {totals[2]} source documents "
          f"with relationships {'affected' if apply else 'would be affected'}.")
    print("Summed counts can include the same source document more than once"
          + (" and the same relationship more than once in a dry run." if not apply else "."))
    if not apply:
        print("Dry run only. Re-run with --apply to write.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete matching graph data from the real DB")
    args = parser.parse_args()
    db = DBFactory.get_prod_db_mongo()
    try:
        clean(db, args.apply)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
