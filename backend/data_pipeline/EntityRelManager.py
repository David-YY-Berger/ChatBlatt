from typing import Dict, List

from backend.models.EntityObjects.Entity import Entity
from backend.models.Enums import EntityType, SourceType
from backend.models.Rel import Rel
from backend.db.DBFactory import DBFactory
from backend.common.Decorators import singleton


@singleton
class EntityRelManager:
    def __init__(self):
        self.db_api = DBFactory.get_prod_db_mongo()

    def get_entity_from_key(self, entity_key:str) -> Entity | None:
        return None

    def get_rel_from_key(self, entity_key:str) -> Rel | None:
        return None

    def insert_entity(self, entity_key:str, src_type:SourceType) -> str:
        """ returns key """
        # if exists, add to appearances..
        return ""

    def insert_rel(self, entity_key:str, src_type:SourceType) -> str:
        """ returns key """
        # if exists, add to appearances..
        return ""

    def insert_entity_map(self, entity_map: Dict[EntityType, List], src_type:SourceType) -> list[str]:
        """ returns keys """
        return []

    def insert_rel_map(self, rel_map: List[Rel], src_type:SourceType) -> list[str]:
        """ returns keys """
        return []