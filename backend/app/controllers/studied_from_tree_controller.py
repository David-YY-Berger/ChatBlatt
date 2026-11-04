# bs"d - lehagdil torah velahadir

"""
StudiedFromTreeController

Entry-point for studied-from graph requests. Validates the person key and
depth, delegates to StudiedFromTreeLogic.
"""

from __future__ import annotations

from typing import Optional

from backend.app.logic.studied_from_tree_logic import StudiedFromTreeLogic
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.models_dto.StudiedFromGraphData import StudiedFromGraphData


class StudiedFromTreeController:
    def __init__(self, db: Optional[DBapiMongoDB] = None):
        self._logic = StudiedFromTreeLogic(db=db)

    def get_studied_from_graph(
        self,
        center_person_key: str,
        depth: int = 1,
    ) -> StudiedFromGraphData:
        """Returns an empty graph if the key is blank; depth is clamped to 1-2."""
        if not center_person_key:
            return StudiedFromGraphData()

        depth = max(1, min(int(depth), 2))
        return self._logic.build_graph(center_key=center_person_key, depth=depth)
