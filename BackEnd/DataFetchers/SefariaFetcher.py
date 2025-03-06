from typing import Any

import requests
from BackEnd.General import Logger


class SefariaFetcher:

    def __init__(self):
        self.BASE_URL = "https://www.sefaria.org/api/texts"
        self.logger = Logger.Logger()

    def fetch_talmud_daf_as_RAW(self, tractate: str, daf: str) -> Any | None:

        url = f"{self.BASE_URL}/{tractate}.{daf}?context=0"
        response = requests.get(url)

        if response.status_code == 200:
            self.logger.log(f"got {tractate} daf {daf}")
            return response.json()
        else:
            self.logger.error(f"Error fetching {tractate} {daf}: {response.status_code}")
            return None

    def get_source_from_passage_str(self, passage_str):

        foo =''

    # def fetch_talmud_daf_as_SOURCE(self, tractate: str, daf: str) -> Any | None:
    #     raw_json = self.fetch_talmud_daf_as_RAW(tractate, daf)
    #     # todo convert to source
    #     return
    #
    # def fetch_talmud_daf_range(self, tractate: str, start_daf: str, end_daf: str) -> str:
    #
    #     dafs = SefariaFetcher.generate_daf_range(start_daf, end_daf)
    #     result = {}
    #
    #     for daf in dafs:
    #         data = self.fetch_talmud_daf_as_RAW(tractate, daf)
    #         if data:
    #             result[daf] = {
    #                 "hebrew": data.get("he", []),
    #                 "english": data.get("text", [])
    #             }
    #
    #     return json.dumps(result, ensure_ascii=False, indent=4)

    # @staticmethod
    # def generate_daf_range(start_daf: str, end_daf: str) -> list:
    #
    #     start_num = int(start_daf[:-1])
    #     start_side = start_daf[-1]
    #
    #     end_num = int(end_daf[:-1])
    #     end_side = end_daf[-1]
    #
    #     dafs = []
    #     for num in range(start_num, end_num + 1):
    #         if num == start_num and start_side == "b":
    #             dafs.append(f"{num}b")
    #         else:
    #             dafs.append(f"{num}a")
    #             dafs.append(f"{num}b")
    #
    #     if end_side == "a":
    #         dafs.pop()  # Remove last "b" if end_daf is "a"
    #
    #     return dafs
