"""Remove stored family relationships involving one entity from the real DB.

Run from the project root:
    python -m backend_pipeline.data_pipeline.one_time_scripts.remove_entity_family_relationships ENTITY_KEY

The default is a read-only preview. After reviewing it, repeat with --apply.
Stop graph population and back up the Graphs database before applying. This
does not prevent future population from recreating the relationships.
"""
import argparse

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields
from backend.db.DBFactory import DBFactory
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.models_db.Enums import FAMILY_REL_TYPES


def clean(db, entity_key: str, apply: bool) -> None:
    if not entity_key or not entity_key.strip() or entity_key != entity_key.strip():
        raise ValueError("Provide a non-empty entity key without surrounding whitespace")

    def cleanup():
        entities = db.get_collection(CollectionObjs.ENTITIES)
        relations = db.get_collection(CollectionObjs.RELATIONS)
        metadata = db.get_collection(CollectionObjs.SRC_METADATA)
        entity = entities.find_one({DBFields.KEY: entity_key})
        if entity is None:
            raise ValueError(f"Entity {entity_key!r} not found")
        query = {
            "$or": [{DBFields.TERM1: entity_key}, {DBFields.TERM2: entity_key}],
            DBFields.REL_TYPE: {"$in": [rel_type.value for rel_type in FAMILY_REL_TYPES]},
        }
        rels = list(relations.find(query))
        rel_keys = []
        for rel in rels:
            key = rel.get(DBFields.KEY)
            if not isinstance(key, str) or not key:
                raise ValueError(f"Relationship {rel['_id']} has no usable key")
            if relations.count_documents({DBFields.KEY: key}) != 1:
                raise ValueError(f"Relationship key {key!r} is not unique")
            rel_keys.append(key)

        source_count = metadata.count_documents({DBFields.REL_KEYS: {"$in": rel_keys}}) if rel_keys else 0
        if apply and rels:
            metadata.update_many(
                {DBFields.REL_KEYS: {"$in": rel_keys}},
                {"$pull": {DBFields.REL_KEYS: {"$in": rel_keys}}},
            )
            result = relations.delete_many({"_id": {"$in": [rel["_id"] for rel in rels]}})
            if result.deleted_count != len(rels):
                raise RuntimeError("Not all selected relationships were deleted")
        return entity, rels, source_count

    entity, rels, source_count = db.run_in_transaction(cleanup) if apply else cleanup()
    print(f"Entity: {entity.get(DBFields.DISPLAY_EN_NAME, '')} ({entity_key})")
    for rel in rels:
        print(f"  {rel[DBFields.KEY]}: {rel[DBFields.TERM1]} "
              f"--{rel[DBFields.REL_TYPE]}--> {rel[DBFields.TERM2]}")
    print(f"{'Removed' if apply else 'Would remove'} {len(rels)} relationships; "
          f"{source_count} source metadata documents {'updated' if apply else 'would be updated'}.")
    if not apply:
        print("Dry run only. Re-run with --apply to write.")


def main(entity_key: str = "", apply: bool = False) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entity_key", nargs="?", default=entity_key, help="The entity's database key")
    parser.add_argument("--apply", action="store_true", help="Delete from the real database")
    args = parser.parse_args()
    db = DBapiMongoDB(DBFactory.get_population_mongo_uri(), ensure_indexes=False)
    try:
        clean(db, args.entity_key, apply or args.apply)
    finally:
        db.disconnect()


if __name__ == "__main__":
    ENTITY_KEY = "6ae8a96f545535391e1dc65e"  # god
    # APPLY = False
    APPLY = True  # Uncomment to delete from the real DB
    main(ENTITY_KEY, APPLY)
