# bs"d - lehagdil torah velahadir
import os

############################################## local Computer output paths #######################################
BASE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Chatblatt")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")
TESTS_DIR = os.path.join(BASE_DIR, "Tests")
QUESTIONS_OUTPUT_DIR = os.path.join(TESTS_DIR, "Questions")


############################################## local paths for this project #######################################

current_file = os.path.abspath(__file__) #paths.py
GENERAL_DIR = os.path.dirname(current_file)
BACKEND_DIR= os.path.dirname(GENERAL_DIR)
PROJECT_ROOT_DIR = os.path.dirname(BACKEND_DIR)
MONGO_QUERIES_DIR = os.path.join(BACKEND_DIR, "data_pipeline/mongo_queries")
QA1_PATH = os.path.join(GENERAL_DIR, "../", "QA", "QA_Question_Sheet.csv")

EXAMPLES_DIR = os.path.join(PROJECT_ROOT_DIR, "Examples")
TEST_DATA_BEREISHIT_DIR = os.path.join(EXAMPLES_DIR, "testDataBereishit")
TEST_DATA_BEREISHIT_ENTITY_REL_DIR = os.path.join(TEST_DATA_BEREISHIT_DIR, "EntityAndRels")
TEST_DATA_BEREISHIT_METADATA_DIR = os.path.join(TEST_DATA_BEREISHIT_DIR, "metadata")

ENTITIES_TO_IGNORE_DIR = os.path.join(
    PROJECT_ROOT_DIR, "backend_pipeline", "data_pipeline", "PydanticModels", "entities_to_ignore"
)

COMMON_ENTITY_PRE_POPULATE_DIR = os.path.join(
    PROJECT_ROOT_DIR, "backend_pipeline", "data_pipeline", "common_entity_pre_populate"
)
AMBIGUOUS_TANACH_CHARACTERS_JSON = os.path.join(
    COMMON_ENTITY_PRE_POPULATE_DIR, "ambiguous_tanach_characters.json"
)

############################################## real-data populator output (per-book) #######################################
# Single central root for every LLM-populator script's JSON/TXT output, so changing where this
# data lives is a one-line edit here instead of hunting down hardcoded paths in each script.
# Sibling folder to the repo (not under version control) - distinct from TESTS_DIR above, which
# is for throwaway/debug output (e.g. get_examples_src_contents runs), not real population runs.
REAL_DATA_DIR = os.path.join(os.path.dirname(PROJECT_ROOT_DIR), "ChatBlatt_data_files", "real_data")
ENTITY_REL_GRAPH_REAL_DATA_DIR = os.path.join(REAL_DATA_DIR, "entity_rels")
ENTITY_ENRICHMENT_REAL_DATA_DIR = os.path.join(REAL_DATA_DIR, "enrichment")


def get_entity_rel_graph_output_dir(book_database_name: str) -> str:
    """Per-book output dir for DBPopulateEntityRelGraph's phase 1/2 JSON+TXT files."""
    return os.path.join(ENTITY_REL_GRAPH_REAL_DATA_DIR, book_database_name.lower())


def get_entity_enrichment_output_dir(book_database_name: str) -> str:
    """Per-book output dir for DBPopulateEntityEnrichment's phase 1/2 JSON+TXT files."""
    return os.path.join(ENTITY_ENRICHMENT_REAL_DATA_DIR, book_database_name.lower())


BACKUP_OF_SRC_CONTENT = os.path.join(BASE_DIR, r"\DB_backups\backup_of_src_contents_TN_BT.json")

QA_MONGO_QUERIES = os.path.join(MONGO_QUERIES_DIR, "qa_mongo_queries.json")
DATA_CLEANUP_MONGO_QUERIES = os.path.join(MONGO_QUERIES_DIR, "data_cleanup_mongo_queries.json")
DATA_ANALYSIS_MONGO_QUERIES = os.path.join(MONGO_QUERIES_DIR, "data_analysis_mongo_queries.json")

############################################## local paths - for 1 time scripts #######################################
SEFARIA_INDEX_BT_PASSAGES = r"C:\Users\U6072661\PycharmProjects\ChatBlatt\dataIndexFiles\BT_passages_index.json"
# SEFARIA_INDEX_BT_PASSAGES = r"C:\Users\dberg\OneDrive\Documentos\ChatBlatt\data_index_files\BT_passages_index.json"
GLOSSARY_TEMP = os.path.join(TESTS_DIR, "Glossary.csv")

def get_test_output_path(test_name, file_ext):
    return os.path.join(TESTS_DIR, f"{test_name}.{file_ext}")