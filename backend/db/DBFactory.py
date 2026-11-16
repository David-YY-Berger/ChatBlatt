# bs'd
import subprocess
from datetime import datetime
from urllib.parse import quote_plus

from backend.db.DBapiMongoDB import DBapiMongoDB
from system_common.SystemFunctions import get_secret


class DBFactory:

    @staticmethod
    def _get_mongo_uri(username_env: str, password_env: str) -> str:
        username = get_secret(username_env)
        password = get_secret(password_env)
        if not username or not password:
            raise ValueError(f"Missing database credentials: {username_env} and {password_env}")

        uri = (
            f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}"
            "@chatblatt.sdqpvk2.mongodb.net/?retryWrites=true&w=majority&appName=ChatBlatt"
        )
        return uri

    @staticmethod
    def get_prod_mongo_uri() -> str:
        return DBFactory._get_mongo_uri("DB_READ_ONLY_USERNAME", "DB_READ_ONLY_PASSWORD")

    @staticmethod
    def get_population_mongo_uri() -> str:
        return DBFactory._get_mongo_uri("DB_BT_USERNAME", "DB_BT_PASSWORD")

    @staticmethod
    def get_prod_db_mongo() -> DBapiMongoDB:
        uri = DBFactory.get_prod_mongo_uri()
        return DBapiMongoDB(uri, ensure_indexes=False)

    @staticmethod
    def get_population_db_mongo() -> DBapiMongoDB:
        uri = DBFactory.get_population_mongo_uri()
        return DBapiMongoDB(uri, ensure_indexes=True)

    # #2
    # @staticmethod
    # def get_test_db_mongo() -> DBapiMongoDB:
    #
    #     # Retrieve the database username and password from environment variables
    #     username = get_secret('DB_BT_USERNAME')
    #     password = get_secret('DB_BT_PASSWORD')
    #
    #     # MongoDB URI
    #     uri = (
    #         f"mongodb+srv://{username}:{password}"
    #         "@chatblatt.sdqpvk2.mongodb.net/?retryWrites=true&w=majority&appName=ChatBlatt"
    #     )
    #
    #     return DBapiMongoDB(uri)

    @staticmethod
    def run_mongo_dump():
        uri = DBFactory.get_population_mongo_uri()

        # Output folder: backup_YYYYMMDD_HHMMSS
        out_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Construct the system command
        command = [
            r"C:\mongodb-database-tools-windows-x86_64-100.13.0\bin\mongodump.exe",  # full path
            f"--uri={uri}",
            f"--out={out_dir}"
        ]

        print("Running mongodump...")
        subprocess.run(command, check=True)

        print(f"Backup completed. Files stored in: {out_dir}")

    if __name__ == "__main__":
        run_mongo_dump()