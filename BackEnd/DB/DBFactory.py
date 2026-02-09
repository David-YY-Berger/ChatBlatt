# bs'd
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

from BackEnd.DB.DBapiMongoDB import DBapiMongoDB


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

    @staticmethod
    def run_mongo_dump():
        load_dotenv()

        username = os.getenv("DB_BT_USERNAME")
        password = os.getenv("DB_BT_PASSWORD")

        if not username or not password:
            raise ValueError("Missing DB credentials in .env")

        uri = (
            f"mongodb+srv://{username}:{password}"
            "@chatblatt.sdqpvk2.mongodb.net/?retryWrites=true&w=majority&appName=ChatBlatt"
        )

        # Output folder: backup_YYYYMMDD_HHMMSS
        out_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Construct the system command
        command = [
            r"C:\mongodb-database-tools-windows-x86_64-100.13.0\bin\mongodump.exe",  # full path
            f"--uri={uri}",
            f"--out={out_dir}"
        ]

        print("Running:", " ".join(command))
        subprocess.run(command, check=True)

        print(f"Backup completed. Files stored in: {out_dir}")

    if __name__ == "__main__":
        run_mongo_dump()