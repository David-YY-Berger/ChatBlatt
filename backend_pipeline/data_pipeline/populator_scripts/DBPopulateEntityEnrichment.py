# bs"d
"""
DBPopulateEntityEnrichment - Enrich existing entities with attributes derived from passages.

Two-phase workflow (inherited from DBPopulateLlmBase):
  Phase 1 (test_run_extraction):  iterate sources -> call LLM -> save JSON files
  Phase 2 (test_populate_from_jsons): load JSON files -> update DB entities

For each source, the LLM is given a passage (clean English + clean Hebrew, no vowels)
plus the JSON of any associated entities (Person/Number/Place/Symbol, ...) that have not
yet been enriched. Each JSON file contains an EnrichmentResponse (entities: [...]) keyed
by entity 'key', filling in fields like display_heb_name, Person.timePeriod/isWoman/
isNonJew/isGroup/roles, Number.heb_unit/heb_context, Place.placeType, Symbol.symbolType.
Phase 2 resolves each entry back to a DB entity by key and patches its fields.
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

    async def _extract_from_passage(self, passage: str, entity_json_list: Optional[List[str]] = None):
        """
        *passage* is expected to already contain BOTH the clean English and clean
        Hebrew (no vowels) text of the source. *entity_json_list* is a list of JSON
        strings — one per DB entity associated with this passage that has not yet
        been enriched with metadata (e.g. Person/Number/Place/Symbol entities pulled
        from this source's SourceMetadata.entity_keys).
        """
        return await self.enrichment_caller.extract_from_passage(passage, entity_json_list)

    def _process_json_entries(self, json_entries: List[Tuple[str, dict]]) -> None:
        pass

    # --- Enrichment helpers ---------------------------------------------------


