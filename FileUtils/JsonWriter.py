import json

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
