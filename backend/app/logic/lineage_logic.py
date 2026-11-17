# bs"d - lehagdil torah velahadir
"""Directed parent-child traversal for lineage searches."""

from collections import deque

from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.models_db.Enums import RelType
from backend.models_db.Rel import Rel
from backend.models_dto.EntitySelectOption import EntitySelectOption

PARENT_REL_TYPES = (RelType.childOfFather, RelType.childOfMother)


class LineageGraph:
    def __init__(self, options: list[EntitySelectOption], rels: list[Rel]):
        self.options = {option.key: option for option in options}
        self.children: dict[str, set[str]] = {}
        self.parents: dict[str, set[str]] = {}
        self.relationships: dict[tuple[str, str], set[str]] = {}
        for rel in rels:
            child, parent = rel.term1, rel.term2
            if (rel.rel_type not in PARENT_REL_TYPES or child == parent
                    or child not in self.options or parent not in self.options):
                continue
            self.children.setdefault(parent, set()).add(child)
            self.parents.setdefault(child, set()).add(parent)
            if rel.key:
                self.relationships.setdefault((parent, child), set()).add(rel.key)

    def start_options(self, descendants: bool) -> list[EntitySelectOption]:
        adjacency = self.children if descendants else self.parents
        return [option for key, option in self.options.items() if key in adjacency]

    def paths_from(self, start: str, descendants: bool) -> dict[str, str | None]:
        """Return BFS predecessors, including the start, for shortest directed paths."""
        adjacency = self.children if descendants else self.parents
        predecessors: dict[str, str | None] = {start: None}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency.get(current, ())):
                if neighbor not in predecessors:
                    predecessors[neighbor] = current
                    queue.append(neighbor)
        return predecessors


def load_lineage_graph(db: DBapiMongoDB) -> LineageGraph:
    options = db.getPersonSelectOptions()
    rels = db.get_rels_by_type_for_entities(
        [option.key for option in options],
        [rel_type.value for rel_type in PARENT_REL_TYPES],
        as_term1=True, as_term2=False,
    )
    return LineageGraph(options, rels)


def lineage_path(predecessors: dict[str, str | None], target: str) -> list[str]:
    path = []
    current: str | None = target
    while current is not None:
        path.append(current)
        current = predecessors[current]
    return list(reversed(path))
