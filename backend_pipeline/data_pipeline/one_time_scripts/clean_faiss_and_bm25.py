"""Clear the persisted FAISS and BM25 indexes for both supported languages.

Writes to the REAL DB only when run with --apply (or when APPLY is set to True
below). This does not modify source documents.
"""
import sys

from backend.bm25_api import BM25Engine
from backend.db.DBFactory import DBFactory
from backend.faiss_api import FaissEngine


def main(apply: bool) -> None:
    if not apply:
        print("Dry run only. Re-run with --apply to clear all FAISS and BM25 indexes.")
        return

    db = DBFactory.get_prod_db_mongo()
    try:
        FaissEngine.FaissEngine(dbapi=db).clear_index()
        print("Cleared FAISS indexes for English and Hebrew.")
        BM25Engine.BM25Engine(dbapi=db).clear_index()
        print("Cleared BM25 indexes for English and Hebrew.")
    finally:
        db.disconnect()


if __name__ == "__main__":
    # Set True to run directly from an IDE; otherwise pass --apply.
    APPLY = False
    main(APPLY or "--apply" in sys.argv)
