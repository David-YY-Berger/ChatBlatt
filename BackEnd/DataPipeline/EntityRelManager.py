from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.Rel import Rel
from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.General.Decorators import singleton


@singleton
class EntityRelManager:
    def __init__(self, db: DBapiInterface):
        self.db_api = db

    def get_entity_from_id(self, entity_id) -> Entity | None:
        return None

    def get_rel_from_id(self, entity_id) -> Rel | None:
        return None
