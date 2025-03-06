import json
import bson
from bson import ObjectId


class JsonWriter:
    """
    A static class for writing Python dictionaries to JSON files.
    """
    @staticmethod
    def write_to_file(data, file_path, indent=4):
        """
        Writes a dictionary to a JSON file.

        :param data: Dictionary to be written to the JSON file.
        :param file_path: Path to the JSON file.
        :param indent: Indentation level for pretty printing (default is 4).
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=indent, ensure_ascii=False)
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
        """Convert a BSON file to a JSON file, handling MongoDB ObjectId."""

        # Read BSON file
        with open(input_bson_path, "rb") as bson_file:
            data = bson.decode_all(bson_file.read())

        # Convert ObjectId to string
        def convert_mongo_types(obj):
            if isinstance(obj, ObjectId):  # Convert ObjectId to string
                return str(obj)
            elif isinstance(obj, dict):  # Recursively handle nested dictionaries
                return {k: convert_mongo_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):  # Recursively handle lists
                return [convert_mongo_types(i) for i in obj]
            return obj  # Return other types as-is

        data = convert_mongo_types(data)  # Apply conversion

        # Write to JSON file
        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)

        print(f"Converted {input_bson_path} to {output_json_path}")
