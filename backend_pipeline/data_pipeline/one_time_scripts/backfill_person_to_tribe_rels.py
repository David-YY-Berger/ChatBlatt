"""One-time backfill: populate the personToTribeOfIsrael relationships the population pipeline dropped.

Cause: DBPopulateEntityRelGraph resolves rel terms by NAME only, and the Person category is checked
before TribeOfIsrael - so "Gershom -> Levi" pointed at Levi the *Person* (or was dropped), never at the
TribeOfIsrael entity. Only same-name Person/Tribe pairs (e.g. "judah" -> "judah") ended up correct.

For every JSON in real_data/entity_rels, this resolves term1 (any Person entity of that source, by name)
and term2 (the TribeOfIsrael entity of that source, by name) via the source's SourceMetadata.entity_keys
and inserts the missing rel (try_insert_rel dedups) + adds its key to the source's SourceMetadata.rel_keys.
It touches nothing else.

Writes to the REAL DB (there is no test DB). Dry-run by default; pass --apply to write
(or set `APPLY = True` at the bottom, e.g. when running from PyCharm).
"""
import json
import os
import sys
from typing import Dict, List, Optional

from backend.common import Paths
from backend.db.DBFactory import DBFactory
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType, RelType
from backend.models_db.Rel import Rel

REL_FIELD = RelType.personToTribeOfIsrael.value


def _names(entity: Entity) -> set:
    names = {(entity.display_en_name or "").strip().lower()}
    names.update((n or "").strip().lower() for n in (getattr(entity, "all_en_names", None) or []))
    names.discard("")
    return names


def _find(name: str, entities: List[Entity], entity_type: EntityType) -> List[Entity]:
    name = name.strip().lower()
    return [e for e in entities if e.entityType == entity_type and name in _names(e)]


def _load_jsons() -> List[tuple]:
    """(path, source_key, res) for every entity-rel JSON that has personToTribeOfIsrael rels."""
    found = []
    for root, _, files in os.walk(Paths.ENTITY_REL_GRAPH_REAL_DATA_DIR):
        for file_name in sorted(files):
            if not file_name.endswith(".json"):
                continue
            path = os.path.join(root, file_name)
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
            res = data.get("res", data)
            if (res.get("Rel") or {}).get(REL_FIELD):
                found.append((path, data.get("key") or file_name[:-5].replace(";", ":"), res))
    return found


def backfill(db, apply: bool) -> None:
    jsons = _load_jsons()
    print(f"{len(jsons)} source files contain {REL_FIELD} rels\n")
    created = existing = unresolved = missing_meta = 0

    for path, source_key, res in jsons:
        metadata = db.get_source_metadata_by_key(source_key)
        if metadata is None:
            print(f"[no SourceMetadata] {source_key} - skipped")
            missing_meta += 1
            continue
        entities = db.get_entities_by_keys(list(metadata.entity_keys))
        new_rel_keys: Dict[str, str] = {}

        for rel_data in res["Rel"][REL_FIELD]:
            term1_name = (rel_data.get("term1") or "").strip()
            term2_name = (rel_data.get("term2") or "").strip()
            persons = _find(term1_name, entities, EntityType.EPerson)
            tribes = _find(term2_name, entities, EntityType.ETribeOfIsrael)
            if len(persons) != 1 or len(tribes) != 1:
                print(f"  [unresolved] {source_key}: '{term1_name}' -> '{term2_name}' "
                      f"({len(persons)} person match, {len(tribes)} tribe match)")
                unresolved += 1
                continue
            person, tribe = persons[0], tribes[0]
            if person.key == tribe.key:
                continue

            rel = Rel.create(rel_type=RelType.personToTribeOfIsrael, term1=person.key, term2=tribe.key)
            already = db._find_existing_rel_key(rel)
            if already:
                existing += 1
                key = already
            elif apply:
                key = db.try_insert_rel(rel)
                created += 1
            else:
                key = None
                created += 1
            print(f"  {'exists ' if already else ('CREATED' if apply else 'would create')} "
                  f"{person.display_en_name} -> {tribe.display_en_name}  ({source_key})")
            if key and key not in metadata.rel_keys:
                new_rel_keys[key] = key

        if apply and new_rel_keys:
            metadata.rel_keys = set(metadata.rel_keys) | set(new_rel_keys)
            db.update_source_metadata(metadata)

    verb = "created" if apply else "would be created"
    print(f"\nDone: {created} {verb}, {existing} already existed, {unresolved} unresolved, "
          f"{missing_meta} sources without SourceMetadata.")
    if not apply:
        print("Dry run only. Re-run with --apply to write.")


def main(apply: bool) -> None:
    db = DBFactory.get_prod_db_mongo()
    try:
        backfill(db, apply)
    finally:
        db.disconnect()


if __name__ == "__main__":
    APPLY = False  # set True (or pass --apply) to actually write to the DB
    main(APPLY or "--apply" in sys.argv)
