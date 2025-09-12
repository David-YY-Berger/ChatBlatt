from BackEnd.General import Logger
from BackEnd.FileUtils import FileTypeEnum
from pathlib import Path
import json


def print_to_file(content, file_type: FileTypeEnum.FileType, file_path: str):
    if not isinstance(file_type, FileTypeEnum.FileType):
        raise ValueError("Invalid file extension. Use FileType Enum.")

    logger = Logger.Logger()
    path = Path(file_path).with_suffix(f".{file_type.value}")

    try:
        with open(path, "w", encoding="utf-8-sig") as file:
            match file_type:
                case FileTypeEnum.FileType.JSON:
                    json.dump(content, file, ensure_ascii=False, indent=4)
                case FileTypeEnum.FileType.HTML:
                    file.write(content)
                case FileTypeEnum.FileType.TXT:
                    file.write(content)
        logger.log(f"Content successfully written to {path}")
    except Exception as e:
        logger.error(f"Failed to write to file: {e}")