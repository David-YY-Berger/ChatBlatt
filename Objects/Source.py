from enum import Enum


class ContentType(Enum):
    EN_CONTENT = 0
    HEB_CONTENT = 1


class Source:
    def __init__(self, type_: Enum, book: str, chapter: int, section: str, content: list[str]):
        self.type = type_
        self.book = book
        self.chapter = chapter
        self.section = section
        self.content = content

    def get_key(self) -> str:
        return f"{self.type.name}{self.book}{self.chapter}{self.section}"

    @staticmethod
    def get_empty_src(key: str):
        # Assuming key is structured as type+book+chapter+section
        return Source(
            type_=None,  # Type should be determined based on key
            book="",  # Extract book from key if needed
            chapter=0,  # Placeholder, adjust parsing as required
            section="",
            content=[]
        )
