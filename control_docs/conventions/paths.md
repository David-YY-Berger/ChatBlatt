# Paths - always via `backend/common/Paths.py`

**Every file/dir path used by code lives in `backend/common/Paths.py`.** Never hardcode a path (or build one with
`os.path.dirname(__file__)`) inside a script. Before adding or using a path, open `Paths.py` and check if it exists;
if not, add a named constant (or a small `get_..._dir(...)` helper for parameterized ones) following the existing pattern,
then `from backend.common import Paths` in the script. Derive from `PROJECT_ROOT_DIR` (repo files) or `REAL_DATA_DIR`
(non-versioned real output). Document the new path in the doc of the feature that uses it.

Notable constants: `REAL_DATA_DIR` (+ `ENTITY_REL_GRAPH_REAL_DATA_DIR`, `ENTITY_ENRICHMENT_REAL_DATA_DIR`),
`MERGE_CSV_DIR`, `MERGE_REVIEW_DIR`, `COMMON_ENTITY_PRE_POPULATE_DIR`, `ENTITIES_TO_IGNORE_DIR`, `DB_BACKUPS_DIR`, `TESTS_DIR`.