from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from backend.common import Paths
from backend.db.Collections import CollectionObjs


DEFAULT_OUTPUT_DIR = Path(Paths.REAL_DATA_DIR) / "display_db"


def text(value: Any) -> str:
    """Keep database values from changing Markdown structure."""
    if value is None or not str(value).strip():
        return "(not available)"
    result = " ".join(str(value).split())
    for char in "\\`*_{}[]<>#|":
        result = result.replace(char, "\\" + char)
    return result


def entity_label(entity: Mapping[str, Any]) -> str:
    return (f"{text(entity.get('display_en_name'))} | "
            f"{text(entity.get('display_heb_name'))} | "
            f"{text(entity.get('entityType'))} | key: {text(entity.get('key'))}")


def load_documents(db: Any, relationship_types: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rels = list(db.get_collection(CollectionObjs.RELATIONS).find(
        {"rel_type": {"$in": relationship_types}},
        {"_id": 0, "key": 1, "term1": 1, "term2": 1, "rel_type": 1},
    ))
    entity_keys = {rel[field] for rel in rels for field in ("term1", "term2")}
    entities = list(db.get_collection(CollectionObjs.ENTITIES).find(
        {"key": {"$in": list(entity_keys)}},
        {"_id": 0, "key": 1, "entityType": 1, "display_en_name": 1, "display_heb_name": 1},
    ))
    return entities, rels


def index_entities(entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_key = {}
    for entity in entities:
        key = entity.get("key")
        if not isinstance(key, str) or not key or key in by_key:
            raise ValueError(f"Entity has a missing or duplicate key: {key!r}")
        by_key[key] = entity
    return by_key
