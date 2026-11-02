"""One-time cleanup: trim every SourceContent.content[] down to [EN_html, HEB_html].

A past mistake left some docs with a 3rd element (clean English, `SourceContentType.EN_CLEAN`).
This drops everything past index 1 in the TN and BT collections.

Writes to the REAL DB (there is no test DB). Dry-run by default; to write, uncomment
`APPLY = True` at the bottom (e.g. when running from PyCharm) or pass --apply.
"""
import sys

from backend.db.Collections import CollectionObjs
from backend.db.DBFactory import DBFactory
from backend.models_db.Enums import SourceContentType

KEEP = SourceContentType.EN_CLEAN.value  # number of leading elements to keep (EN, HEB)
EXTRA_FILTER = {f"content.{KEEP}": {"$exists": True}}


def main(apply: bool) -> None:
    db = DBFactory.get_prod_db_mongo()
    try:
        for collection in (CollectionObjs.TN, CollectionObjs.BT):
            col = db.get_collection(collection)
            count = col.count_documents(EXTRA_FILTER)
            # sanity: the first 2 elements must be strings before we trust them
            bad = col.count_documents({
                **EXTRA_FILTER,
                "$or": [
                    {"content.0": {"$not": {"$type": "string"}}},
                    {"content.1": {"$not": {"$type": "string"}}},
                ],
            })
            print(f"{collection.name}: {count} docs with >{KEEP} content elements "
                  f"({bad} with non-string EN/HEB, will be skipped)")
            if not apply or count == 0:
                continue

            result = col.update_many(
                {
                    **EXTRA_FILTER,
                    "content.0": {"$type": "string"},
                    "content.1": {"$type": "string"},
                },
                [{"$set": {"content": {"$slice": ["$content", KEEP]}}}],
            )
            print(f"{collection.name}: modified {result.modified_count}")

        if not apply:
            print("Dry run only. Re-run with --apply to write.")
    finally:
        db.disconnect()


if __name__ == "__main__":
    # APPLY = False  # set True (or pass --apply) to actually write to the DB
    APPLY = True
    main(APPLY or "--apply" in sys.argv)
