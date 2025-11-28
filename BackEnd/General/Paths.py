import os

############################################## local Computer output paths #######################################
BASE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Chatblatt")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")
TESTS_DIR = os.path.join(BASE_DIR, "Tests")
QUESTIONS_OUTPUT_DIR = os.path.join(TESTS_DIR, "Questions")
LMM_RESPONSES_OUTPUT_DIR = os.path.join(TESTS_DIR, "LMM Responses")


############################################## local paths for this project #######################################

current_file = os.path.abspath(__file__) #paths.py
GENERAL_DIR = os.path.dirname(current_file)
BACKEND_DIR= os.path.dirname(GENERAL_DIR)
MONGO_QUERIES_DIR = os.path.join(BACKEND_DIR, "DataPipeline/mongo_queries")
QA1_PATH = os.path.join(GENERAL_DIR, "../", "QA", "QA_Question_Sheet.csv")

QA_MONGO_QUERIES = os.path.join(MONGO_QUERIES_DIR, "qa_mongo_queries.json")
DATA_CLEANUP_MONGO_QUERIES = os.path.join(MONGO_QUERIES_DIR, "data_cleanup_mongo_queries.json")
DATA_ANALYSIS_MONGO_QUERIES = os.path.join(MONGO_QUERIES_DIR, "data_analysis_mongo_queries.json")

############################################## local paths - for 1 time scripts #######################################
SEFARIA_INDEX_BT_PASSAGES = r"C:\Users\U6072661\PycharmProjects\ChatBlatt\dataIndexFiles\BT_passages_index.json"
# SEFARIA_INDEX_BT_PASSAGES = r"C:\Users\dberg\OneDrive\Documentos\ChatBlatt\dataIndexFiles\BT_passages_index.json"
GLOSSARY_TEMP = os.path.join(TESTS_DIR, "Glossary.csv")

def get_test_output_path(test_name, file_ext):
    return os.path.join(TESTS_DIR, f"{test_name}.{file_ext}")