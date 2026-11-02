"""Cleanup: drop all entities, relationships and source metadata objs from the DB.

Run before re-populating the entity-rel graph from scratch.

Writes to the REAL DB (there is no test DB). Dry-run by default; pass --apply to write
(or set `APPLY = True` at the bottom, e.g. when running from PyCharm).
"""
import sys

from backend.db.DBFactory import DBFactory


def clean_entity_rel_graph(db_api) -> tuple:
    """Drop all entities, rels and source metadata. Returns (entities, rels, source_metadata) deleted counts."""
    deleted_entities = db_api.drop_all_entities()
    deleted_rels = db_api.drop_all_rels()
    deleted_src_metadata = db_api.drop_all_source_metadata()
    print(f"Dropped {deleted_entities} entities, {deleted_rels} rels and "
          f"{deleted_src_metadata} source metadata objs.")
    return deleted_entities, deleted_rels, deleted_src_metadata


def main(apply: bool) -> None:
    if not apply:
        print("Dry run only. Re-run with --apply to drop all entities, rels and source metadata.")
        return
    db = DBFactory.get_prod_db_mongo()
    try:
        clean_entity_rel_graph(db)
    finally:
        db.disconnect()


if __name__ == "__main__":
    # APPLY = False  # set True (or pass --apply) to actually write to the DB
    APPLY = True
    main(APPLY or "--apply" in sys.argv)
