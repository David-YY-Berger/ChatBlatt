from BackEnd.DataObjects.EntityObjects.Entity import Entity
from BackEnd.DataObjects.NER import NER
from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.General.Decorators import singleton


@singleton
class EntityNERManager:
    def __init__(self, db: DBapiInterface):
        self.db_api = db

    def get_entity_from_id(self, entity_id) -> Entity | None:
        return None

    def get_ner_from_id(self, entity_id) -> NER | None:
        return None
