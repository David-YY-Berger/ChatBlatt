import os

from dotenv import load_dotenv

from BackEnd.DataPipeline.DB.DBapiInterface import DBapiInterface
from BackEnd.DataPipeline.DB.DBapiMongoDB import DBapiMongoDB


class DBFactory:

    @staticmethod
    def get_prod_db_mongo() -> DBapiMongoDB:
        load_dotenv()

        # Retrieve the database username and password from environment variables
        username = os.getenv('DB_BT_USERNAME')
        password = os.getenv('DB_BT_PASSWORD')

        # MongoDB URI
        uri = (
            f"mongodb+srv://{username}:{password}"
            "@chatblatt.sdqpvk2.mongodb.net/?retryWrites=true&w=majority&appName=ChatBlatt"
        )

        return DBapiMongoDB(uri)

    # #2
    # @staticmethod
    # def get_test_db_mongo() -> DBapiMongoDB:
    #     load_dotenv()
    #
    #     # Retrieve the database username and password from environment variables
    #     username = os.getenv('DB_BT_USERNAME')
    #     password = os.getenv('DB_BT_PASSWORD')
    #
    #     # MongoDB URI
    #     uri = (
    #         f"mongodb+srv://{username}:{password}"
    #         "@chatblatt.sdqpvk2.mongodb.net/?retryWrites=true&w=majority&appName=ChatBlatt"
    #     )
    #
    #     return DBapiMongoDB(uri)