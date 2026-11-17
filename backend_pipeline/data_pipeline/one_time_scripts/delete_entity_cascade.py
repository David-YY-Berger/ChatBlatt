"""Delete one entity, all its relationships, and their SourceMetadata references from the real DB.

Run from the project root:
    python -m backend_pipeline.data_pipeline.one_time_scripts.delete_entity_cascade ENTITY_KEY [--apply]

Or set ENTITY_KEY / APPLY at the bottom (e.g. when running from an IDE).
This is a dry run unless --apply is passed or APPLY is True. Stop graph population and
back up the Graphs database before applying. Everything is deleted in one transaction.
Other entities' alias_keys that point at the deleted entity are not touched; they are listed in the output.
"""
import argparse

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields
from backend.db.DBFactory import DBFactory
from backend.db.DBapiMongoDB import DBapiMongoDB


def clean(db, entity_key: str, apply: bool) -> None:
    if not entity_key or not entity_key.strip() or entity_key != entity_key.strip():
        raise ValueError("Provide a non-empty entity key without surrounding whitespace")

    def cleanup():
        entities = db.get_collection(CollectionObjs.ENTITIES)
        relations = db.get_collection(CollectionObjs.RELATIONS)
        metadata = db.get_collection(CollectionObjs.SRC_METADATA)
        matches = list(entities.find({DBFields.KEY: entity_key}))
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one entity with key {entity_key!r}, found {len(matches)}")
        entity = matches[0]

        rels = list(relations.find({"$or": [{DBFields.TERM1: entity_key}, {DBFields.TERM2: entity_key}]}))
        rel_keys = []
        for rel in rels:
            key = rel.get(DBFields.KEY)
            if not isinstance(key, str) or not key:
                raise ValueError(f"Relationship {rel['_id']} has no usable key")
            if relations.count_documents({DBFields.KEY: key}) != 1:
                raise ValueError(f"Relationship key {key!r} is not unique")
            rel_keys.append(key)

        aliased_by = list(entities.find({"alias_keys": entity_key}))
        entity_sources = metadata.count_documents({DBFields.ENTITY_KEYS: entity_key})
        rel_sources = metadata.count_documents({DBFields.REL_KEYS: {"$in": rel_keys}}) if rel_keys else 0
        if apply:
            metadata.update_many({DBFields.ENTITY_KEYS: entity_key},
                                 {"$pull": {DBFields.ENTITY_KEYS: entity_key}})
            if rel_keys:
                metadata.update_many({DBFields.REL_KEYS: {"$in": rel_keys}},
                                     {"$pull": {DBFields.REL_KEYS: {"$in": rel_keys}}})
                result = relations.delete_many({"_id": {"$in": [rel["_id"] for rel in rels]}})
                if result.deleted_count != len(rels):
                    raise RuntimeError("Not all selected relationships were deleted")
            if entities.delete_one({"_id": entity["_id"]}).deleted_count != 1:
                raise RuntimeError(f"Failed to delete entity {entity_key!r}")
        return entity, rels, entity_sources, rel_sources, aliased_by

    entity, rels, entity_sources, rel_sources, aliased_by = (
        db.run_in_transaction(cleanup) if apply else cleanup()
    )
    print(f"Entity: {entity.get(DBFields.DISPLAY_EN_NAME, '')} "
          f"[{entity.get(DBFields.ENTITY_TYPE, '')}] ({entity_key})")
    for rel in rels:
        print(f"  {rel[DBFields.KEY]}: {rel[DBFields.TERM1]} "
              f"--{rel[DBFields.REL_TYPE]}--> {rel[DBFields.TERM2]}")
    verb = "Deleted" if apply else "Would delete"
    print(f"{verb} the entity and {len(rels)} relationships; {entity_sources} source metadata documents "
          f"{'lose' if apply else 'would lose'} the entity, {rel_sources} lose relationship references.")
    print(f"NOT cleaned up: alias_keys of other entities that point at {entity_key} are left unchanged "
          f"({len(aliased_by)} entities currently reference it).")
    for other in aliased_by:
        print(f"  {other.get(DBFields.KEY)}: {other.get(DBFields.DISPLAY_EN_NAME, '')}")
    if not apply:
        print("Dry run only. Re-run with --apply or set APPLY = True to write.")


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
    ENTITY_KEY = ""  # paste the entity key here
    APPLY = False
    # APPLY = True  # Uncomment to delete from the real DB
    main(ENTITY_KEY, APPLY)
