"""Read-only validation of stored entity relationship consistency."""
from dataclasses import dataclass
from itertools import combinations
from typing import Dict, Iterable, List, Mapping, Set, Tuple

from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields

FATHER_REL = "childOfFather"
MOTHER_REL = "childOfMother"
PARENT_REL_TYPES = {FATHER_REL, MOTHER_REL}
STUDIED_FROM_REL = "studiedFrom"


@dataclass(frozen=True)
class ValidationIssue:
    check: str
    message: str


def _entity_label(entity_key: str, entities: Mapping[str, dict]) -> str:
    entity = entities.get(entity_key)
    if entity:
        return f"{entity.get(DBFields.DISPLAY_EN_NAME, entity_key)} ({entity_key})"
    return entity_key


def validate_relationships(
    entity_documents: Iterable[dict],
    relationship_documents: Iterable[dict],
) -> List[ValidationIssue]:
    """Return all known gender, family-role, and reciprocal-study violations."""
    entities = {
        entity[DBFields.KEY]: entity
        for entity in entity_documents
        if isinstance(entity.get(DBFields.KEY), str)
    }
    relationships = list(relationship_documents)
    issues: List[ValidationIssue] = []

    parent_edges: Dict[Tuple[str, str], List[dict]] = {}
    parent_roles: Dict[Tuple[str, str], Set[str]] = {}
    studied_edges: Dict[Tuple[str, str], List[dict]] = {}

    for relation in relationships:
        rel_type = relation.get(DBFields.REL_TYPE)
        term1 = relation.get(DBFields.TERM1)
        term2 = relation.get(DBFields.TERM2)
        if not isinstance(term1, str) or not isinstance(term2, str):
            continue

        if rel_type in PARENT_REL_TYPES:
            edge = (term1, term2)
            parent_edges.setdefault(edge, []).append(relation)
            parent_roles.setdefault(edge, set()).add(rel_type)

            parent = entities.get(term2)
            is_woman = parent.get("isWoman") if parent else None
            if (rel_type == FATHER_REL and is_woman is True) or (
                rel_type == MOTHER_REL and is_woman is False
            ):
                expected = "male" if rel_type == FATHER_REL else "female"
                issues.append(
                    ValidationIssue(
                        "parent gender",
                        f"{_entity_label(term2, entities)} is recorded as "
                        f"{rel_type} for {_entity_label(term1, entities)} "
                        f"but isWoman={is_woman!r} (expected {expected}); "
                        f"relationship {relation.get(DBFields.KEY, '<no key>')}.",
                    )
                )
        elif rel_type == STUDIED_FROM_REL:
            studied_edges.setdefault((term1, term2), []).append(relation)

    children_by_parent: Dict[str, Set[str]] = {}
    for child, parent in parent_edges:
        children_by_parent.setdefault(parent, set()).add(child)

    sibling_pairs: Set[Tuple[str, str]] = set()
    sibling_relation_keys: Dict[Tuple[str, str], Set[str]] = {}
    for parent, children in children_by_parent.items():
        for first, second in combinations(sorted(children), 2):
            pair = (first, second)
            sibling_pairs.add(pair)
            sibling_relation_keys.setdefault(pair, set()).update(
                relation.get(DBFields.KEY, "<no key>")
                for child in pair
                for relation in parent_edges[(child, parent)]
            )

    family_pairs = {
        tuple(sorted((child, parent)))
        for child, parent in parent_edges
    }
    for first, second in sorted(family_pairs):
        forward = parent_edges.get((first, second), [])
        reverse = parent_edges.get((second, first), [])
        roles = parent_roles.get((first, second), set()) | parent_roles.get((second, first), set())
        reasons = []
        if forward and reverse:
            reasons.append("each entity is recorded as the other's parent")
        if (first, second) in sibling_pairs:
            reasons.append("the entities share a parent and are also recorded as parent/child")
        if FATHER_REL in roles and MOTHER_REL in roles:
            reasons.append("the same entity pair is classified as both father and mother")

        if reasons:
            relation_keys = {
                relation.get(DBFields.KEY, "<no key>")
                for relation in forward + reverse
            }
            if (first, second) in sibling_pairs:
                relation_keys.update(sibling_relation_keys[(first, second)])
            issues.append(
                ValidationIssue(
                    "family relationship",
                    f"{_entity_label(first, entities)} and {_entity_label(second, entities)}: "
                    f"{'; '.join(reasons)}; relationships {', '.join(sorted(relation_keys))}.",
                )
            )

    for first, second in sorted(studied_edges):
        if first >= second or (second, first) not in studied_edges:
            continue
        relation_keys = {
            relation.get(DBFields.KEY, "<no key>")
            for relation in studied_edges[(first, second)] + studied_edges[(second, first)]
        }
        issues.append(
            ValidationIssue(
                "reciprocal studiedFrom",
                f"{_entity_label(first, entities)} and {_entity_label(second, entities)} "
                f"are recorded as studying from each other; relationships "
                f"{', '.join(sorted(relation_keys))}.",
            )
        )

    return issues


def main() -> int:
    from backend.db.DBFactory import DBFactory

    db = DBFactory.get_prod_db_mongo()
    try:
        entities = db.get_collection(CollectionObjs.ENTITIES)
        relations = db.get_collection(CollectionObjs.RELATIONS)
        issues = validate_relationships(entities.find({}), relations.find({}))
    finally:
        db.disconnect()

    if issues:
        print(f"Found {len(issues)} relationship validation issue(s):")
        for issue in issues:
            print(f"- [{issue.check}] {issue.message}")
        return 1

    print("No entity relationship validation issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
