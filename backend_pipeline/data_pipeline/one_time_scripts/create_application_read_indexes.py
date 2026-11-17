"""Create source-content lookup indexes; run from the repository root.

Dry-run by default. Pass --apply or set APPLY = True to create missing indexes.
"""
import argparse

from pymongo import ASCENDING, MongoClient

from backend.db.Collections import CollectionObjs
from backend.db.DBFactory import DBFactory


INDEX_NAME = "idx_source_content_key"
INDEX_KEYS = [("key", ASCENDING)]
SOURCE_COLLECTIONS = (CollectionObjs.TN, CollectionObjs.BT)


def has_usable_key_index(indexes) -> bool:
    for index in indexes:
        keys = list(index["key"].items())
        collation = index.get("collation", {})
        if (
            keys[:1] == INDEX_KEYS
            and not index.get("hidden")
            and not index.get("sparse")
            and "partialFilterExpression" not in index
            and (not collation or collation.get("locale") == "simple")
        ):
            return True
    return False


def create_missing_indexes(db, apply: bool) -> None:
    existing_collections = set(db.list_collection_names())
    for collection_info in SOURCE_COLLECTIONS:
        name = collection_info.name
        if name not in existing_collections:
            raise RuntimeError(f"Sources.{name} does not exist; refusing to create a collection")

    for collection_info in SOURCE_COLLECTIONS:
        name = collection_info.name
        collection = db[name]
        indexes = list(collection.list_indexes())
        if has_usable_key_index(indexes):
            print(f"Sources.{name}: usable key index already exists; skipping")
            continue
        if any(index["name"] == INDEX_NAME or list(index["key"].items()) == INDEX_KEYS for index in indexes):
            raise RuntimeError(f"Sources.{name}: conflicting key index exists; inspect it before proceeding")
        if apply:
            created = collection.create_index(INDEX_KEYS, name=INDEX_NAME)
            print(f"Sources.{name}: created {created}")
        else:
            print(f"Sources.{name}: would create {INDEX_NAME} on {INDEX_KEYS}")


def main(apply: bool = False) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="create indexes in the real database")
    args = parser.parse_args()
    apply = apply or args.apply

    uri = DBFactory.get_population_mongo_uri() if apply else DBFactory.get_prod_mongo_uri()
    with MongoClient(uri, serverSelectionTimeoutMS=10000) as client:
        create_missing_indexes(client[CollectionObjs.TN.db_name], apply)
    if not apply:
        print("Dry run only; pass --apply or set APPLY = True to create the missing indexes.")


if __name__ == "__main__":
    APPLY = False  # Set True to create indexes when running from an IDE.
    main(APPLY)
