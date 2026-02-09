import base64
import gzip
import json
import bson
from bson import ObjectId


class JsonWriter:
    """
        A static class for writing Python dictionaries to JSON files.
        """

    @staticmethod
    def write_to_file(data, file_path, indent=4, append=False, write_log=True):
        """
        Writes a dictionary to a JSON file. Optionally appends the data instead of overwriting.

        :param data: Dictionary to be written to the JSON file.
        :param file_path: Path to the JSON file.
        :param indent: Indentation level for pretty printing (default is 4).
        :param append: Whether to append the data to the file (default is False).
        """
        try:
            if append:
                # Read the existing data from the file, if present
                try:
                    with open(file_path, 'r', encoding='utf-8') as json_file:
                        existing_data = json.load(json_file)
                except (FileNotFoundError, json.JSONDecodeError):
                    existing_data = []

                # Append the new data
                existing_data.append(data)

                # Write back the updated data
                with open(file_path, 'w', encoding='utf-8') as json_file:
                    json.dump(existing_data, json_file, indent=indent, ensure_ascii=False)
            else:
                # Overwrite the file with the new data
                with open(file_path, 'w', encoding='utf-8') as json_file:
                    json.dump(data, json_file, indent=indent, ensure_ascii=False)

            if write_log:
                print(f"Successfully wrote JSON data to {file_path}")
        except Exception as e:
            print(f"Error writing JSON to file: {e}")


    @staticmethod
    def write_to_string(data, indent=4):
        """
        Converts a dictionary to a JSON-formatted string.

        :param data: Dictionary to be converted.
        :param indent: Indentation level for pretty printing (default is 4).
        :return: JSON string representation of the dictionary.
        """
        try:
            return json.dumps(data, indent=indent, ensure_ascii=False)
        except Exception as e:
            print(f"Error converting dictionary to JSON string: {e}")
            return None

    @staticmethod
    def bson_to_json(input_bson_path: str, output_json_path: str):
        """Convert a gzipped BSON file to JSON, handling ObjectIds and Bytes."""
        data = []

        with gzip.open(input_bson_path, "rb") as bson_file:
            for doc in bson.decode_file_iter(bson_file):
                data.append(doc)

        def convert_mongo_types(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, bytes):
                # Convert bytes to a base64 string so JSON can save it
                return base64.b64encode(obj).decode('utf-8')
            elif isinstance(obj, dict):
                return {k: convert_mongo_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_mongo_types(i) for i in obj]
            return obj

        data = convert_mongo_types(data)

        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
