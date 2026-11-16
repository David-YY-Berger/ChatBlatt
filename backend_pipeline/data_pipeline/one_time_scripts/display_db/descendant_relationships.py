"""Export stored descendantOf relationships from the production DB.

Run from the project root:
    python -m backend_pipeline.data_pipeline.one_time_scripts.display_db.descendant_relationships

Reports are written under real_data/display_db in the sibling data-files directory.
Use --output-dir to choose another directory. The database is never modified.
"""
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from backend.db.DBFactory import DBFactory
from backend.models_db.Enums import EntityType, RelType
from backend_pipeline.data_pipeline.one_time_scripts.display_db.report_helpers import (
    DEFAULT_OUTPUT_DIR, entity_label, index_entities, load_documents,
)


def build_reports(entities: List[Dict[str, Any]], rels: List[Dict[str, Any]]) -> Dict[str, str]:
    by_key = index_entities(entities)
    descendants: Dict[str, List[str]] = defaultdict(list)
    ancestors: Dict[str, List[str]] = defaultdict(list)
    for rel in rels:
        descendant, ancestor = rel["term1"], rel["term2"]
        for key in (descendant, ancestor):
            if key not in by_key:
                raise ValueError(f"Relationship {rel.get('key')!r} references missing entity {key!r}")
            if by_key[key].get("entityType") != EntityType.EPerson.value:
                raise ValueError(f"Relationship {rel.get('key')!r} references non-person entity {key!r}")
        descendants[ancestor].append(descendant)
        ancestors[descendant].append(ancestor)

    def render(title: str, label: str, groups: Dict[str, List[str]]) -> str:
        sort_name = lambda key: (str(by_key[key].get("display_en_name") or "").casefold(), key)
        keys = sorted(groups, key=lambda key: (-len(groups[key]), *sort_name(key)))
        lines = [
            f"# People with the most {title}",
            "",
            f"{len(keys)} people with at least one stored descendantOf relationship in this direction.",
            "Counts are stored relationship records, not inferred ancestry; parent/child relationships "
            "are not included.",
            "Each item shows English name | Hebrew name | entity type | entity key.",
            "",
        ]
        for key in keys:
            related = sorted(groups[key], key=sort_name)
            lines.extend([f"## {entity_label(by_key[key])}", "", f"**{label}: {len(related)}**", ""])
            lines.extend(f"- {entity_label(by_key[target])}" for target in related)
            lines.extend(["", "---", ""])
        return "\n".join(lines)

    return {
        "descendants.md": render("descendants", "Descendants", descendants),
        "ancestors.md": render("ancestors", "Ancestors", ancestors),
    }


def export_reports(db: Any, output_dir: Path) -> List[Path]:
    entities, rels = load_documents(db, [RelType.descendantOf.value])
    reports = build_reports(entities, rels)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, report in reports.items():
        path = output_dir / filename
        path.write_text(report, encoding="utf-8")
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
