# bs"d - lehagdil torah velahadir

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class GenealogyNode(BaseModel):
    """A single person-node in the genealogy graph."""
    key: str
    display_name: str
    is_center: bool = False
    is_woman: bool = False


class GenealogyEdge(BaseModel):
    """A directed or symmetric relationship edge between two nodes."""
    from_key: str
    to_key: str
    rel_type: str   # e.g. "childOfFather", "childOfMother", "spouseOf", "sibling"
    label: str = ""


class GenealogyGraphData(BaseModel):
    """Full graph payload returned by MapGenealogyLogic to the frontend."""
    nodes: List[GenealogyNode] = Field(default_factory=list)
    edges: List[GenealogyEdge] = Field(default_factory=list)
    center_key: str = ""
