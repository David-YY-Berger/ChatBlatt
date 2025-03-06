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
        print(f"Directory does not exist: {dir_path}")

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)