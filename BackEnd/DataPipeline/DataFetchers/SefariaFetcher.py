import re
from typing import Any
from collections import defaultdict

import requests

from BackEnd.DataObjects.SourceClasses.SourceClass import SourceClass
from BackEnd.General import Logger
from BackEnd.DataObjects.SourceClasses import SourceContent
from BackEnd.DataObjects.SourceClasses.SourceContent import SourceContent

from BackEnd.DataObjects.Enums import SourceType, SourceContentType


class SefariaFetcher:

    def __init__(self):
        self.TEXTS_BASE_URL = "https://www.sefaria.org/api/texts"
        self.logger = Logger.Logger()
        self.temp_daf_data = None
        self.session = requests.session()


    def fetch_talmud_daf_as_RAW(self, tractate: str, daf: str) -> Any | None:
        url = f"{self.TEXTS_BASE_URL}/{tractate}.{daf}?context=0"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Error fetching {tractate} {daf}\n\tURL: {url}\n\tResponse code: {response.status_code}")
            return None

    def fetch_tanach_chapter_as_RAW(self, book: str, chapter: str) -> Any | None:
        url = f"{self.TEXTS_BASE_URL}/{book}.{chapter}?context=0"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Error fetching {book} {chapter}\n\tURL: {url}\n\tResponse code: {response.status_code}")
            return None


    def fetch_sefaria_passage_as_Source_from_data(self, json_data) -> SourceContent:

        if json_data['type'] == "Mishnah" or json_data['type'] == "Sugya":
            return self.fetch_BT_as_Source_from_ref(json_data['full_ref'])
        elif json_data['type'] == "biblical-story":
            return self.fetch_TN_as_Source_from_ref_list(full_ref=json_data['full_ref'], ref_list=json_data['ref_list'])
        else:
            self.logger.error(f"Unknown type {json_data['type']}")
            raise Exception(f"Unknown type {json_data['type']}")


    def fetch_BT_as_Source_from_ref(self, reference) -> SourceContent:
        """ function poorly done... should be refactored to use list from sefaria's .json file"""
        [tractate, sections] = self.parse_talmud_reference(reference)
        content = ["", ""]

        for daf in sections:
            if not self.temp_daf_data or self.temp_daf_data[0] != tractate or self.temp_daf_data[1] != daf:
                self.temp_daf_data = [tractate, daf, self.fetch_talmud_daf_as_RAW(tractate=tractate, daf=daf)]

            if not self.temp_daf_data[2] or "text" not in self.temp_daf_data[2]:
                continue

            start_section, end_section = sections[daf]
            start_index = int(start_section) - 1
            end_index = int(end_section) - 1 if end_section else len(self.temp_daf_data[2]["text"])

            for i in range(start_index, end_index + 1):
                if i < len(self.temp_daf_data[2]['text']):
                    en_content_from_section = self.temp_daf_data[2]['text'][i]
                    heb_content_from_section = self.temp_daf_data[2]['he'][i]
                    # FOR DEBUGGING print(f"printing {tractate} {daf} {start_index} - {end_index} {data_from_section}")
                    content[SourceContentType.EN.value] += en_content_from_section
                    content[SourceContentType.HEB.value] += heb_content_from_section

        key = SourceClass.get_key_from_details(src_type=SourceType.BT, book=tractate, chapter=0,
                                                 section=reference.split(tractate, 1)[1].strip())
        return SourceContent(key = key, content=content)


    def fetch_TN_as_Source_from_ref_list(self, full_ref: str, ref_list : list) -> SourceContent:

        match = re.match(r'^(.*?)(?=\d)', full_ref)
        if match:
            book = match.group(1).strip()
            section = full_ref[len(book) + 1:].strip()
        else:
            raise Exception(f"Invalid reference {full_ref}")

        dic = self.extract_chapter_verse_ranges(ref_list)
        en_content = ""
        heb_content = ""
        for (chapter, verse_range) in dic.items():
            json_data = self.fetch_tanach_chapter_as_RAW(book=book, chapter=chapter)
            en_json = json_data['text']
            heb_json = json_data['he']

            en_content += self.extract_verses_from_chapter(en_json, verse_range)
            heb_content += self.extract_verses_from_chapter(heb_json, verse_range)

        content = ["", ""]
        content[SourceContentType.EN.value] += en_content
        content[SourceContentType.HEB.value] += heb_content

        # TODO must add chapter here!
        # raise RuntimeError("Must add chapter!")
        key = SourceClass.get_key_from_details(src_type=SourceType.TN, book=book, chapter=0, section=section)
        return SourceContent(key=key, content=content)

    def extract_chapter_verse_ranges(self, ref_list):
        """
        Extracts chapter-to-verse ranges from a list of references like 'BookName Chapter:Verse'.

        Parameters:
            ref_list (List[str]): List of reference strings (e.g., "Joshua 3:1").

        Returns:
            Dict[int, Tuple[int, int]]: Dictionary where keys are chapter numbers,
                                        and values are (min_verse, max_verse) tuples.
        """
        chapter_verses = defaultdict(list)

        for ref in ref_list:
            match = re.search(r'(\d+):(\d+)$', ref)
            if match:
                chapter = int(match.group(1))
                verse = int(match.group(2))
                chapter_verses[chapter].append(verse)

        # Convert to dictionary with (min, max) verse tuples
        return {chapter: (min(verses) -1 , max(verses) - 1) for chapter, verses in chapter_verses.items()}

    def extract_verses_from_chapter(self, data: dict, verse_range: tuple) -> str:

        start, end = verse_range
        res = data[start:end + 1]
        return " ".join(res)


    def parse_talmud_reference(self, reference: str):
        """
        Bava Batra 2a:1-5 -> ('Bava Batra', {'2a': ('1', 5)})
        Bava Batra 2a:6-2b:6 -> ('Bava Batra', {'2a': ('6', None), '2b': ('1', '6')})
        """

        if reference.count(":") == 1:

            if reference.count("-") == 0:
                match = re.match(r"^([A-Za-z ]+) (\d+[a-b]):(\d+)$", reference)
                if not match:
                    raise ValueError("Invalid format")
                tractate, start_daf, start_section = match.groups()
                sections = {start_daf: (start_section, start_section)}
                return tractate, sections

            elif reference.count("-") == 1:
                # Case for single daf (e.g., "Bava Batra 2a:1-5")
                match = re.match(r"^([A-Za-z ]+) (\d+[a-b]):(\d+)-(\d+)$", reference)
                if not match:
                    raise ValueError("Invalid format")

                tractate, start_daf, start_section, end_section = match.groups()
                sections = {start_daf: (start_section, end_section)}
                return tractate, sections
            else:
                raise ValueError("Invalid format")

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

