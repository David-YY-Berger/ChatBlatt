# bs"d
"""Dump every collection of the prod Mongo DB to .bson files.

Run:  python -m backend_pipeline.data_pipeline.backup_scripts.BackupDB   (from repo root)

Output:  <DB_BACKUPS_DIR>/<YYYY-MM-DD_HH-MM-SS>/<db_name>/<collection>.bson
         <DB_BACKUPS_DIR>/<YYYY-MM-DD_HH-MM-SS>/README.md   <- edit: describe what this backup includes
Read-only against the DB. Restore with: mongorestore --uri=... <timestamp_folder>
"""
import os
from datetime import datetime

import bson

from backend.common import Paths
from backend.db.DBFactory import DBFactory

SYSTEM_DBS = {"admin", "local", "config"}
BATCH_SIZE = 1000

README_TEMPLATE = """# Backup {stamp}

## What this backup includes
<!-- Write here: why this backup was taken, DB state (e.g. "after Bereishit entity-rel-graph"), etc. -->

## Contents
{contents}
"""


def backup_all() -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(Paths.DB_BACKUPS_DIR, stamp)
    os.makedirs(backup_dir, exist_ok=True)

    db = DBFactory.get_prod_db_mongo()
    contents = []
    try:
        for db_name in sorted(set(db.client.list_database_names()) - SYSTEM_DBS):
            db_dir = os.path.join(backup_dir, db_name)
            os.makedirs(db_dir, exist_ok=True)
            for coll_name in sorted(db.client[db_name].list_collection_names()):
                count = _dump_collection(db.client[db_name][coll_name], os.path.join(db_dir, f"{coll_name}.bson"))
                contents.append(f"- `{db_name}/{coll_name}.bson` - {count} docs")
                print(f"{db_name}.{coll_name}: {count} docs")
    finally:
        db.client.close()

    with open(os.path.join(backup_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(README_TEMPLATE.format(stamp=stamp, contents="\n".join(contents)))

    print(f"Backup completed: {backup_dir}")
    return backup_dir


def _dump_collection(collection, path: str) -> int:
    count = 0
    with open(path, "wb") as f:
        for doc in collection.find({}, batch_size=BATCH_SIZE):
            f.write(bson.encode(doc))
            count += 1
    return count


if __name__ == "__main__":
    backup_all()
