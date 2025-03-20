import re
from typing import Any

import requests
from BackEnd.General import Logger
from BackEnd.Objects.Source import Source, SourceType, SourceContentType


class SefariaFetcher:

    def __init__(self):
        self.TEXTS_BASE_URL = "https://www.sefaria.org/api/texts"
        self.logger = Logger.Logger()

    def fetch_talmud_daf_as_RAW(self, tractate: str, daf: str) -> Any | None:

        url = f"{self.TEXTS_BASE_URL}/{tractate}.{daf}?context=0"
        response = requests.get(url)

        if response.status_code == 200:
            # self.logger.log(f"got {tractate} daf {daf}")
            return response.json()
        else:
            self.logger.error(f"Error fetching {tractate} {daf}: {response.status_code}")
            return None

    def fetch_sefaria_passage_as_Source_from_reference(self, reference):

        [tractate, sections] = self.parse_talmud_reference(reference)
        for daf in sections:
            daf_data = self.fetch_talmud_daf_as_RAW(tractate=tractate, daf=daf)

            if not daf_data or "text" not in daf_data:
                continue

            start_section, end_section = sections[daf]
            start_index = int(start_section) - 1
            end_index = int(end_section) - 1 if end_section else len(daf_data["text"])

            content = ["", ""]

            for i in range(start_index, end_index + 1):
                if i < len(daf_data['text']):
                    data_from_section = daf_data['text'][i]
                    # FOR DEBUGGING print(f"printing {tractate} {daf} {start_index} - {end_index} {data_from_section}")
                    content[SourceContentType.EN_CONTENT.value] +=data_from_section

        #     todo get hebrew content

        return Source(src_type=SourceType.BT, book=tractate, chapter=0,
                      section=reference.split(tractate, 1)[1].strip(), content=content)

    def parse_talmud_reference(self, reference: str):
        """
        Bava Batra 2a:1-5 -> ('Bava Batra', {'2a': ('1', 5)})
        Bava Batra 2a:6-2b:6 -> ('Bava Batra', {'2a': ('6', None), '2b': ('1', '6')})
        """

        if reference.count(":") == 1:
            # Case for single daf (e.g., "Bava Batra 2a:1-5")
            match = re.match(r"^([A-Za-z ]+) (\d+[a-b]):(\d+)-(\d+)$", reference)
            if not match:
                raise ValueError("Invalid format")

            tractate, start_daf, start_section, end_section = match.groups()
            sections = {start_daf: (start_section, end_section)}

            return tractate, sections

        elif reference.count(":") == 2:
            # Case for split daf (e.g., "Bava Batra 2a:6-2b:6")
            match = re.match(r"^([A-Za-z ]+) (\d+[a-b]):(\d+)-(\d+[a-b]):(\d+)$", reference)
            if not match:
                raise ValueError("Invalid format")

            tractate, start_daf, start_section, end_daf, end_section = match.groups()
            sections = {start_daf: (start_section, None), end_daf: ("1", end_section)}

            return tractate, sections
            # # If there's an end daf different from the start daf, add it to the sections
            # if end_daf and end_daf != start_daf:
            #     sections[end_daf] = ("1", end_section)
        else:
            raise ValueError("Invalid format")

