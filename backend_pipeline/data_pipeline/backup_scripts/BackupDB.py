"""Dump the production MongoDB with MongoDB Database Tools.

Run from the repository root:
    python -m backend_pipeline.data_pipeline.backup_scripts.BackupDB

The output can be restored with:
    mongorestore --uri="<MongoDB URI>" <timestamp_directory>
"""
import os
import shutil
import subprocess
from datetime import datetime

from backend.common import Paths
from backend.db.DBFactory import DBFactory

SYSTEM_DATABASES = ("admin", "config", "local")

README_TEMPLATE = """# Backup {stamp}

## What this backup includes
<!-- Describe why this backup was taken and the database state. -->

## Databases
{databases}
"""


def backup_all() -> str:
    mongodump = shutil.which("mongodump")
    if mongodump is None:
        raise FileNotFoundError(
            "mongodump was not found on PATH. Install MongoDB Database Tools and ensure mongodump is available."
        )

    uri = DBFactory.get_prod_mongo_uri()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(Paths.DB_BACKUPS_DIR, stamp)
    os.makedirs(backup_dir, exist_ok=False)

    command = [
        mongodump,
        f"--uri={uri}",
        f"--out={backup_dir}",
        *(f"--nsExclude={db_name}.*" for db_name in SYSTEM_DATABASES),
    ]
    subprocess.run(command, check=True)

    database_names = sorted(
        name for name in os.listdir(backup_dir)
        if os.path.isdir(os.path.join(backup_dir, name))
    )
    with open(os.path.join(backup_dir, "README.md"), "w", encoding="utf-8") as readme:
        readme.write(
            README_TEMPLATE.format(
                stamp=stamp,
                databases="\n".join(f"- `{name}/`" for name in database_names),
            )
        )

    print(f"Backup completed: {backup_dir}")
    return backup_dir


if __name__ == "__main__":
    backup_all()
