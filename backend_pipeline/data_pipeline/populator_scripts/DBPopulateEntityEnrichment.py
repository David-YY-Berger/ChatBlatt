# bs"d
"""
DBPopulateEntityEnrichment - Enrich existing Person entities with attributes derived from passages.

Two-phase workflow (inherited from DBPopulateLlmBase):
  Phase 1 (test_run_extraction):  iterate sources -> call LLM -> save JSON files
  Phase 2 (test_populate_from_jsons): load JSON files -> update DB entities

Each JSON file contains an EnrichmentResponse (people: [...]) for one source.
Phase 2 resolves each person entry to a DB entity by name and patches its fields.
"""

from typing import List, Optional, Tuple

from backend.common import Paths
from backend.models_db.Enums import EntityType, RoleType, TimePeriod
from backend_pipeline.data_pipeline.llm_api.EntityEnrichmentCaller import EntityEnrichmentCaller
from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
from backend_pipeline.data_pipeline.populator_scripts.DBPopulateLlmBase import DBPopulateLlmBase


class DBPopulateEntityEnrichment(DBPopulateLlmBase):
    """
    Populator script that enriches existing Person entities in the DB with
    attributes extracted by an LLM from source passages.

    Inherits the two-phase scaffold from DBPopulateLlmBase.
    """

    def setUp(self):
        super().setUp()

        # ====== SWITCH MODEL HERE ======
        ModelConfig.set_provider(ModelProvider.GEMINI_FREE)
        # ModelConfig.set_provider(ModelProvider.GEMINI_PAID)
        # ModelConfig.set_provider(ModelProvider.OPENAI)
        # ===============================

        self.enrichment_caller = EntityEnrichmentCaller()

    def tearDown(self):
        super().tearDown()

    # --- DBPopulateLlmBase abstract method implementations --------------------

    def _get_output_dir(self) -> str:
        return Paths.ENRICHMENT_RESPONSES_OUTPUT_DIR

    async def _extract_from_passage(self, passage: str):
        return await self.enrichment_caller.extract_from_passage(passage)

    def _process_json_entries(self, json_entries: List[Tuple[str, dict]]) -> None:
        pass

    # --- Enrichment helpers ---------------------------------------------------


