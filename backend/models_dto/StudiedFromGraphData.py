# bs"d - lehagdil torah velahadir

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StudiedFromNode(BaseModel):
    """A single person-node in the studied-from graph."""
    key: str
    display_name: str
    display_heb_name: str = ""
    is_center: bool = False
    is_woman: Optional[bool] = None  # None = unknown gender (not yet enriched)


class StudiedFromEdge(BaseModel):
    """
    Relationship edge. "studiedFrom" edges run student (from_key) -> teacher
    (to_key), as stored; "disagreedWith" edges are symmetric.
    """
    from_key: str
    to_key: str
    rel_type: str   # "studiedFrom" or "disagreedWith"
    label: str = ""


class StudiedFromGraphData(BaseModel):
    """Full graph payload returned by StudiedFromTreeLogic to the frontend."""
    nodes: List[StudiedFromNode] = Field(default_factory=list)
    edges: List[StudiedFromEdge] = Field(default_factory=list)
    center_key: str = ""
