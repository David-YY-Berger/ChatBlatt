"""Export comparison, contrast and alias relationships from the production DB.

Run from the project root:
    python -m backend_pipeline.data_pipeline.one_time_scripts.display_db.comparison_relationships

Reports are written under real_data/display_db in the sibling data-files directory.
Use --output-dir to choose another directory. The database is never modified.
"""
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from backend.db.DBFactory import DBFactory
from backend.models_db.Enums import EntityType, RelType
from backend_pipeline.data_pipeline.one_time_scripts.display_db.report_helpers import (
    DEFAULT_OUTPUT_DIR, entity_label, index_entities, load_documents, text,
)


RELATIONSHIPS = (
    (RelType.comparedTo.value, "Compared to", "Compared to this entity"),
    (RelType.contrastedWith.value, "Contrasted with", "Contrasted with this entity"),
    (RelType.AliasOf.value, "Alias of", "Has this entity as an alias"),
)
def build_reports(
    entities: List[Dict[str, Any]],
    relationships: Iterable[Mapping[str, Any]],
) -> Dict[str, str]:
    """Build one report per entity type, including empty reports for repeat runs."""
    by_key = index_entities(entities)
    types = {entity_type.value for entity_type in EntityType}
    for key, entity in by_key.items():
        if entity.get("entityType") not in types:
            raise ValueError(f"Entity {key!r} has an unknown entity type: {entity.get('entityType')!r}")

    # Each record contributes once to the count of each participating entity.
    entries: Dict[str, Dict[Tuple[str, str], List[str]]] = defaultdict(lambda: defaultdict(list))
    counts: Dict[str, int] = defaultdict(int)
    relationship_types = {rel_type for rel_type, _, _ in RELATIONSHIPS}
    for rel in relationships:
        rel_type = rel.get("rel_type")
        if rel_type not in relationship_types:
            continue
        term1, term2 = rel.get("term1"), rel.get("term2")
        if term1 not in by_key or term2 not in by_key:
            raise ValueError(f"Relationship {rel.get('key')!r} has missing entity: {term1!r} -> {term2!r}")
        entries[term1][(rel_type, "outgoing")].append(term2)
        entries[term2][(rel_type, "incoming")].append(term1)
        counts[term1] += 1
        if term1 != term2:
            counts[term2] += 1

    reports = {}
    for entity_type in sorted(types):
        keys = [key for key in entries if by_key[key]["entityType"] == entity_type]
        keys.sort(key=lambda key: (-counts[key], str(by_key[key].get("display_en_name") or "").casefold(), key))
        lines = [
            f"# {text(entity_type)}: comparisons, contrasts and aliases",
            "",
            f"{len(keys)} entities with at least one relationship.",
            "Counts are relationship records across all three types and both directions; "
            "a self-relationship counts once.",
            "Each item shows English name | Hebrew name | entity type | entity key.",
            "",
        ]
        for key in keys:
            lines.extend([f"## {entity_label(by_key[key])}", "", f"**Relationships: {counts[key]}**", ""])
            for rel_type, outgoing_label, incoming_label in RELATIONSHIPS:
                for direction, label in (("outgoing", outgoing_label), ("incoming", incoming_label)):
                    targets = entries[key].get((rel_type, direction), [])
                    if not targets:
                        continue
                    targets = sorted(targets, key=lambda target: (
                        str(by_key[target].get("display_en_name") or "").casefold(), target
                    ))
                    lines.extend([f"### {label} ({len(targets)})", ""])
                    lines.extend(f"- {entity_label(by_key[target])}" for target in targets)
                    lines.append("")
            lines.extend(["---", ""])
        reports[entity_type] = "\n".join(lines)
    return reports


def export_reports(db: Any, output_dir: Path) -> List[Path]:
    entities, rels = load_documents(db, [rel_type for rel_type, _, _ in RELATIONSHIPS])
    reports = build_reports(entities, rels)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for entity_type, text in reports.items():
        path = output_dir / f"{entity_type}.md"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    db = DBFactory.get_population_db_mongo()
    try:
        paths = export_reports(db, args.output_dir)
    finally:
        db.disconnect()
    for path in paths:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
