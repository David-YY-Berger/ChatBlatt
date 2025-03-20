import os

BASE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Chatblatt")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")
TESTS_DIR = os.path.join(BASE_DIR, "Tests")

# local paths - for 1 time scripts
SEFARIA_INDEX_BT_PASSAGES = r"C:\Users\U6072661\PycharmProjects\ChatBlatt\dataIndexFiles\BT_passages_index.json"

def get_test_output_path(test_name, file_ext):
    return os.path.join(TESTS_DIR, f"{test_name}.{file_ext}")