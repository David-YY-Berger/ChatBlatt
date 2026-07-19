# bs"d - lehagdil torah velahadir

"""
MapGenealogyLogic

Builds a GenealogyGraphData for a given Person entity, expanding up to
`depth` hops (N-degree family; the UI currently exposes 1 or 2) using
family relationship types:

  - childOfFather / childOfMother  → directed parent-child edges
  - spouseOf                        → symmetric spouse edges
  - children                        → reverse parent-child (derived)
  - siblings                        → synthetic edges for shared parents

BFS approach (level-by-level, one batched DB query per level):
  1. Start with center person key as the initial frontier (level 0).
  2. For each hop, batch-fetch family rels for the WHOLE frontier at once
     (get_family_rels_for_entities), not one query per node.
  3. Add newly discovered person-nodes and edges to the graph. Only nodes
     that are brand new (not already in the graph) become next frontier.
  4. Repeat for `depth` hops, or until the frontier stops growing.
  5. After BFS, add sibling edges between nodes that share a parent.
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

# Hard ceiling on BFS hops, independent of whatever the UI/controller exposes.
# Prevents pathological/expensive expansion if callers pass a huge depth.
MAX_DEPTH = 10


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
        Build a genealogy graph for the center person up to `depth` hops
        (N-degree family expansion). depth=1 → direct family, depth=2 →
        family of family, depth=3 → their family, etc.

        Args:
            center_key: entity key of the center person.
            depth:      number of BFS hops to expand (clamped to
                        [1, MAX_DEPTH]).

        Returns:
            GenealogyGraphData with nodes and edges ready for rendering.
        """
        depth = max(1, min(depth, MAX_DEPTH))

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

        # `frontier` = keys discovered in the *previous* hop that still need
        # their own relationships expanded this round.
        frontier: Set[str] = {center_key}

        for _ in range(depth):
            if not frontier:
                break  # graph has stopped growing; no point querying further

            # Batch-fetch all family rels touching ANY node in the current
            # frontier in a single DB round-trip (this is what makes 2+ hop
            # "family of family" expansion actually work efficiently).
            rels = self.db.get_family_rels_for_entities(list(frontier))
            rels = [r for r in rels if r.rel_type in _FAMILY_REL_TYPES]

            # Resolve unknown endpoint keys to Entity objects in one batch call
            all_endpoint_keys: Set[str] = set()
            for rel in rels:
                all_endpoint_keys.add(rel.term1)
                all_endpoint_keys.add(rel.term2)
            unknown_keys = [k for k in all_endpoint_keys if k not in nodes]
            entity_map: Dict[str, Entity] = self.db.get_entities_by_keys_map(
                unknown_keys
            )

            new_frontier: Set[str] = set()
            for rel in rels:
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

            # Next hop only needs to expand nodes that are actually new;
            # already-known nodes were expanded in an earlier hop already.
            frontier = new_frontier

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

