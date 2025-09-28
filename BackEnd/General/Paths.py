import os

############################################## local Computer output paths #######################################
BASE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Chatblatt")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")
TESTS_DIR = os.path.join(BASE_DIR, "Tests")
QUESTIONS_OUTPUT_DIR = os.path.join(TESTS_DIR, "Questions")


############################################## local paths for this project #######################################

current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
QA1_PATH = os.path.join(current_dir, "../", "QA", "QA_Question_Sheet.csv")
QA_MONGO_QUERIES = os.path.join(current_dir, "../", "QA", "qa_mongo_queries.json")

############################################## local paths - for 1 time scripts #######################################
SEFARIA_INDEX_BT_PASSAGES = r"C:\Users\U6072661\PycharmProjects\ChatBlatt\dataIndexFiles\BT_passages_index.json"
# SEFARIA_INDEX_BT_PASSAGES = r"C:\Users\dberg\OneDrive\Documentos\ChatBlatt\dataIndexFiles\BT_passages_index.json"
GLOSSARY_TEMP = os.path.join(TESTS_DIR, "Glossary.csv")

def get_test_output_path(test_name, file_ext):
    return os.path.join(TESTS_DIR, f"{test_name}.{file_ext}")