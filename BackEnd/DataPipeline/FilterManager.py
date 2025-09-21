from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.General.Decorators import singleton


@singleton
class FilterManager:
    def __init__(self, db: DBapiInterface):
        self.db_api = db

    # def get_id_from_filter_name(self, filter_name: FilterNames) -> int:
    #     return 0 # make call to db
    #
    # def get_filter_name_from_id(self, id: int) -> FilterNames:
    #     return "" #make call to db