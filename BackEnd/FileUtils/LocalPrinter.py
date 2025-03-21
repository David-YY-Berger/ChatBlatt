from BackEnd.General import Enums, Logger
from pathlib import Path
import json


def print_to_file(content, file_type: Enums.FileType, file_path: str):
    if not isinstance(file_type, Enums.FileType):
        raise ValueError("Invalid file extension. Use FileType Enum.")

    logger = Logger.Logger()
    path = Path(file_path).with_suffix(f".{file_type.value}")

    try:
        with open(path, "w", encoding="utf-8-sig") as file:
            match file_type:
                case Enums.FileType.JSON:
                    json.dump(content, file, ensure_ascii=False, indent=4)
                case Enums.FileType.HTML:
                    file.write(content)
                case Enums.FileType.TXT:
                    file.write(content)
        logger.log(f"Content successfully written to {path}")
    except Exception as e:
        logger.error(f"Failed to write to file: {e}")