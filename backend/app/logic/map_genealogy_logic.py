# bs"d - lehagdil torah velahadir

"""
MapGenealogyLogic

Builds a GenealogyGraphData for a given Person entity, expanding up to
`depth` hops (1 or 2) using family relationship types:

  - childOfFather / childOfMother  → directed parent-child edges
  - spouseOf                        → symmetric spouse edges
  - children                        → reverse parent-child (derived)
  - siblings                        → synthetic edges for shared parents

BFS approach:
  1. Start with center person key.
  2. For each hop, fetch family rels for every frontier node.
  3. Add newly discovered person-nodes and edges to the graph.
  4. After BFS, add sibling edges between nodes that share a parent.
"""

from __future__ import annotations

from typing import Dict, Optional, Set, Tuple

from backend.db.DBFactory import DBFactory
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import RelType
from backend.models_db.Rel import Rel
from backend.models_dto.GenealogyGraphData import GenealogyEdge, GenealogyGraphData, GenealogyNode

# DB rel types included in genealogy graphs
_FAMILY_REL_TYPES: Set[RelType] = {
    RelType.childOfFather,
    RelType.childOfMother,
    RelType.spouseOf,
}

# Human-readable edge labels (for Pyvis)
_EDGE_LABELS: Dict[str, str] = {
    "childOfFather": "Father",
    "childOfMother": "Mother",
    "spouseOf": "Spouse",
    "sibling": "Sibling",
}


class MapGenealogyLogic:
    """
    Builds a genealogy GenealogyGraphData for a given person key.

    Usage:
        logic = MapGenealogyLogic()
        graph_data = logic.build_graph(center_key="abc123", depth=1)
    """

    def __init__(self, db: Optional[DBapiMongoDB] = None):
        self.db: DBapiMongoDB = db or DBFactory.get_prod_db_mongo()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_graph(self, center_key: str, depth: int = 1) -> GenealogyGraphData:
        """
        Build a genealogy graph for the center person up to `depth` hops.

        Args:
            center_key: entity key of the center person.
            depth:      1 = direct family; 2 = family of family.

        Returns:
            GenealogyGraphData with nodes and edges ready for rendering.
        """
        depth = max(1, min(depth, 2))

        # Accumulated state
        nodes: Dict[str, GenealogyNode] = {}   # key → node
        edges: Dict[Tuple, GenealogyEdge] = {}  # (from, to, rel_type) → edge
        # parent_key → set of child keys  (used for sibling computation)
        parent_children: Dict[str, Set[str]] = {}

        # Seed the center node (may not be in DB yet if key is invalid)
        center_entity = self.db.get_entity_by_key(center_key)
        if center_entity is None:
            return GenealogyGraphData(center_key=center_key)

        nodes[center_key] = _make_node(center_entity, is_center=True)

        frontier: Set[str] = {center_key}
        visited: Set[str] = {center_key}

        for _ in range(depth):
            new_frontier: Set[str] = set()
            # Batch-collect all entity keys we'll need
            all_new_keys: Set[str] = set()

            # Fetch rels for every node in the current frontier
            rels_per_node: Dict[str, list] = {}
            for key in frontier:
                rels = self.db.get_family_rels_for_entity(key)
                rels_per_node[key] = rels
                for rel in rels:
                    all_new_keys.add(rel.term1)
                    all_new_keys.add(rel.term2)

            # Resolve unknown keys to Entity objects in one batch call
            unknown_keys = all_new_keys - visited
            entity_map: Dict[str, Entity] = self.db.get_entities_by_keys_map(
                list(unknown_keys)
            )

            # Process each rel
            for key in frontier:
                for rel in rels_per_node.get(key, []):
                    if rel.rel_type not in _FAMILY_REL_TYPES:
                        continue

                    # Add both endpoints as nodes (if they are persons)
                    for endpoint_key in (rel.term1, rel.term2):
                        if endpoint_key not in nodes:
                            entity = entity_map.get(endpoint_key)
                            if entity is not None:
                                nodes[endpoint_key] = _make_node(entity)
                                new_frontier.add(endpoint_key)
                            # If entity not found, we still need the key for edge
                            # but won't add a node for it

                    # Add edge (deduplicate)
                    edge = _make_edge(rel)
                    edge_key = (edge.from_key, edge.to_key, edge.rel_type)
                    rev_edge_key = (edge.to_key, edge.from_key, edge.rel_type)
                    if edge_key not in edges and rev_edge_key not in edges:
                        edges[edge_key] = edge

                    # Track parent→children for sibling computation
                    if rel.rel_type in (RelType.childOfFather, RelType.childOfMother):
                        parent_key = rel.term2
                        child_key = rel.term1
                        parent_children.setdefault(parent_key, set()).add(child_key)

            visited |= set(nodes.keys())
            frontier = new_frontier - visited

        # Add sibling edges between children sharing a parent
        self._add_sibling_edges(parent_children, nodes, edges)

        return GenealogyGraphData(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            center_key=center_key,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_sibling_edges(
        self,
        parent_children: Dict[str, Set[str]],
        nodes: Dict[str, GenealogyNode],
        edges: Dict[Tuple, GenealogyEdge],
    ) -> None:
        """
        For every pair of children sharing at least one parent in the graph,
        add a synthetic sibling edge (if both children are present as nodes).
        """
        added_pairs: Set[frozenset] = set()

        for child_keys in parent_children.values():
            child_list = [k for k in child_keys if k in nodes]
            for i in range(len(child_list)):
                for j in range(i + 1, len(child_list)):
                    pair = frozenset((child_list[i], child_list[j]))
                    if pair in added_pairs:
                        continue
                    added_pairs.add(pair)
                    a, b = child_list[i], child_list[j]
                    edge_key = (a, b, "sibling")
                    edges[edge_key] = GenealogyEdge(
                        from_key=a,
                        to_key=b,
                        rel_type="sibling",
                        label=_EDGE_LABELS["sibling"],
                    )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _make_node(entity: Entity, is_center: bool = False) -> GenealogyNode:
    """Create a GenealogyNode from an Entity."""
    is_woman = getattr(entity, "isWoman", False)
    return GenealogyNode(
        key=entity.key,
        display_name=entity.display_en_name,
        is_center=is_center,
        is_woman=is_woman,
    )


def _make_edge(rel: Rel) -> GenealogyEdge:
    """Create a GenealogyEdge from a Rel."""
    rel_type_str = rel.rel_type.value
    return GenealogyEdge(
        from_key=rel.term1,
        to_key=rel.term2,
        rel_type=rel_type_str,
        label=_EDGE_LABELS.get(rel_type_str, rel_type_str),
    )

