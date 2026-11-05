"""Read-only check: print all relationships whose term2 is a TribeOfIsrael entity, with readable names.

Used to find out whether personToTribeOfIsrael rels that don't show in the UI exist in the DB.
Reads from the REAL DB; writes nothing.
"""
from backend.db.Collections import CollectionObjs
from backend.db.DBFactory import DBFactory

TRIBE_TYPE = "TribeOfIsrael"


def main() -> None:
    db = DBFactory.get_prod_db_mongo()
    try:
        entities = db.get_collection(CollectionObjs.ENTITIES)
        rels = db.get_collection(CollectionObjs.RELATIONS)

        pipeline = [
            {"$lookup": {"from": entities.name, "localField": "term2", "foreignField": "key", "as": "t2"}},
            {"$unwind": "$t2"},
            {"$match": {"t2.entityType": TRIBE_TYPE}},
            {"$lookup": {"from": entities.name, "localField": "term1", "foreignField": "key", "as": "t1"}},
            {"$unwind": {"path": "$t1", "preserveNullAndEmptyArrays": True}},
        ]
        results = list(rels.aggregate(pipeline))

        print(f"Found {len(results)} relationships whose term2 is a {TRIBE_TYPE}\n")
        for r in results:
            t1 = r.get("t1")
            person = f"{t1.get('display_en_name')} ({t1.get('entityType')})" if t1 else f"??? missing entity {r['term1']}"
            flag = "" if r.get("rel_type") == "personToTribeOfIsrael" else "  <-- unexpected rel_type"
            print(f"{person} -> {r['t2'].get('display_en_name')}   "
                  f"[{r.get('rel_type')}, rel {r.get('key')}]{flag}")

        total = rels.count_documents({"rel_type": "personToTribeOfIsrael"})
        print(f"\nTotal personToTribeOfIsrael rels in DB: {total}")
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
