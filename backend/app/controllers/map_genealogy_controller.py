# bs"d - lehagdil torah velahadir

"""
MapGenealogyController

Entry-point for genealogy graph requests.  Accepts a person key and
desired depth, delegates to MapGenealogyLogic, and returns a
GenealogyGraphData ready for the frontend to render.
"""

from __future__ import annotations

from typing import Optional

from backend.app.logic.map_genealogy_logic import MapGenealogyLogic
from backend.db.DBapiMongoDB import DBapiMongoDB
from backend.models_dto.GenealogyGraphData import GenealogyGraphData


class MapGenealogyController:
    """
    Controller for the Genealogy Map feature.

    Validates inputs and delegates graph construction to
    MapGenealogyLogic.
    """

    def __init__(self, db: Optional[DBapiMongoDB] = None):
        self._logic = MapGenealogyLogic(db=db)

    def get_genealogy_graph(
        self,
        center_person_key: str,
        depth: int = 1,
    ) -> GenealogyGraphData:
        """
        Build and return a genealogy graph for the given person.

        Args:
            center_person_key: DB key of the Person entity to centre on.
            depth: Edge-closeness radius — 1 (direct family) or 2 (family of family).

        Returns:
            GenealogyGraphData containing nodes and edges.
            Returns an empty GenealogyGraphData if the key is blank.
        """
        if not center_person_key:
            return GenealogyGraphData()

        depth = max(1, min(int(depth), 2))
        return self._logic.build_graph(center_key=center_person_key, depth=depth)

