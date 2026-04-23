import json
import os, shutil


def clear_create_directory(dir_path):
    """Deletes all files and subdirectories in the given directory."""
    if os.path.exists(dir_path):
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)  # Delete file
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)  # Delete directory
                print(f"Deleted: {item_path}")
            except Exception as e:
                print(f"Error deleting {item_path}: {e}")
    else:
        print(f"Directory does not exist: {dir_path} \nCreating directory at {dir_path}")
        os.makedirs(dir_path)

def create_dir_if_not_exists(dir_path):
    """Creates the directory if it does not exist."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Directory created: {dir_path}")
    else:
        print(f"Directory already exists: {dir_path}")

def open_json_file(filepath):
    """
    Opens a JSON file and returns the parsed data.
    Handles FileNotFoundError and JSONDecodeError.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        raise FileNotFoundError(e)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON - {e}")
        raise json.JSONDecodeError
    return None