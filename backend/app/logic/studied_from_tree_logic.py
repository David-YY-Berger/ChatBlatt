# bs"d - lehagdil torah velahadir

"""
StudiedFromTreeLogic

Builds a StudiedFromGraphData for a Person: teachers above (who they studied
from), students below (who studied from them), and the center person's
disagreements on the center's row.

  - studiedFrom rels are stored student (term1) -> teacher (term2).
  - Upward BFS: for each hop, fetch rels where the frontier is term1 (their teachers).
  - Downward BFS: for each hop, fetch rels where the frontier is term2 (their students).
  - disagreedWith (symmetric) is fetched for the center only; those people are
    not expanded into their own teachers/students.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Set, Tuple

from backend.db.DBFactory import DBFactory
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import RelType
from backend.models_db.Rel import Rel
from backend.models_dto.StudiedFromGraphData import (
    StudiedFromEdge,
    StudiedFromGraphData,
    StudiedFromNode,
)

_EDGE_LABELS: Dict[str, str] = {
    RelType.studiedFrom.value: "Studied from",
    RelType.disagreedWith.value: "Disagreed with",
}

# Hard ceiling on BFS hops, independent of what the UI/controller exposes.
MAX_DEPTH = 10


class StudiedFromTreeLogic:
    def __init__(self, db: Optional[DBapiMongoDB] = None):
        self.db: DBapiMongoDB = db or DBFactory.get_prod_db_mongo()

    def build_graph(self, center_key: str, depth: int = 1) -> StudiedFromGraphData:
        """
        Args:
            center_key: entity key of the center person.
            depth:      hops to expand in both directions (clamped to [1, MAX_DEPTH]).
        """
        depth = max(1, min(depth, MAX_DEPTH))

        center_entity = self.db.get_entity_by_key(center_key)
        if center_entity is None:
            return StudiedFromGraphData(center_key=center_key)

        nodes: Dict[str, StudiedFromNode] = {center_key: _make_node(center_entity, True)}
        edges: Dict[Tuple[str, str, str], StudiedFromEdge] = {}

        studied = RelType.studiedFrom.value
        # Upward: frontier is the student (term1), new people are teachers (term2).
        # Downward: frontier is the teacher (term2), new people are students (term1).
        for upward in (True, False):
            frontier: Set[str] = {center_key}
            for _ in range(depth):
                if not frontier:
                    break
                rels = self.db.get_rels_by_type_for_entities(
                    list(frontier), [studied], as_term1=upward, as_term2=not upward
                )
                frontier = self._add_rels(
                    rels, nodes, edges,
                    far_key=(lambda r: r.term2) if upward else (lambda r: r.term1),
                )

        disagreed = self.db.get_rels_by_type_for_entities(
            [center_key], [RelType.disagreedWith.value]
        )
        self._add_rels(
            disagreed, nodes, edges,
            far_key=lambda r: r.term2 if r.term1 == center_key else r.term1,
        )

        return StudiedFromGraphData(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            center_key=center_key,
        )

    def _add_rels(
        self,
        rels: list,
        nodes: Dict[str, StudiedFromNode],
        edges: Dict[Tuple[str, str, str], StudiedFromEdge],
        far_key: Callable[[Rel], str],
    ) -> Set[str]:
        """
        Adds each rel's far-side entity as a node and the rel as an edge (only
        when both endpoints resolve to entities). Returns the keys of the newly
        added nodes (the next BFS frontier).
        """
        unknown = {far_key(r) for r in rels} - nodes.keys()
        entity_map: Dict[str, Entity] = self.db.get_entities_by_keys_map(list(unknown))

        new_frontier: Set[str] = set()
        for key in unknown:
            entity = entity_map.get(key)
            if entity is not None:
                nodes[key] = _make_node(entity)
                new_frontier.add(key)

        for rel in rels:
            if rel.term1 not in nodes or rel.term2 not in nodes or rel.term1 == rel.term2:
                continue
            edge = _make_edge(rel)
            key = (edge.from_key, edge.to_key, edge.rel_type)
            rev_key = (edge.to_key, edge.from_key, edge.rel_type)
            # disagreedWith is symmetric; studiedFrom is directional
            symmetric = edge.rel_type == RelType.disagreedWith.value
            if key not in edges and not (symmetric and rev_key in edges):
                edges[key] = edge
        return new_frontier


def _make_node(entity: Entity, is_center: bool = False) -> StudiedFromNode:
    return StudiedFromNode(
        key=entity.key,
        display_name=entity.display_en_name,
        display_heb_name=entity.display_heb_name or "",
        is_center=is_center,
        is_woman=getattr(entity, "isWoman", None),
    )


def _make_edge(rel: Rel) -> StudiedFromEdge:
    rel_type_str = rel.rel_type.value
    return StudiedFromEdge(
        from_key=rel.term1,
        to_key=rel.term2,
        rel_type=rel_type_str,
        label=_EDGE_LABELS.get(rel_type_str, rel_type_str),
    )
