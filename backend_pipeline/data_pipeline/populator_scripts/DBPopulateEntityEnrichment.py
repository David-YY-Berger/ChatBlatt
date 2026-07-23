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

import json
import os
from typing import List, Optional, Tuple

from backend.common import Paths
from backend.db.DBConstants import DBFields
from backend.file_utils import FileTypeEnum
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.Enums import EntityType, RoleType, TimePeriod
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend_pipeline.data_pipeline.llm_api.EntityEnrichmentCaller import EntityEnrichmentCaller
from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
from backend_pipeline.data_pipeline.populator_scripts.DBPopulateLlmBase import DBPopulateLlmBase, get_examples_src_contents
from backend_pipeline.file_utils_pipeline import LocalPrinter


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

    # --- Phase 1 override: custom source list + entity filtering --------------

    async def _extract_all_to_json(self) -> None:
        """
        Iterate the example sources (get_examples_src_contents), and for each one:
          - look up its SourceMetadata to find linked entity keys
          - fetch those entities and drop any that already have metadata
          - if nothing is left to enrich, skip the source entirely (saves LLM calls)
          - otherwise call the LLM with the bilingual passage + remaining entities
        Saves JSON and TXT output files under _get_output_dir(), mirroring
        DBPopulateEntityRelGraph's Phase 1 output style.
        """
        total_cost_usd = 0.0
        total_tokens = total_input_tokens = total_output_tokens = 0
        num_processed = num_skipped = 0

        contents = get_examples_src_contents(self.db_api)
        for src_content in contents:
            entities = self._get_unenriched_entities_for_source(src_content.key)
            if not entities:
                print(f"  Skipping {src_content.key}: no entities need enrichment.")
                num_skipped += 1
                continue

            entity_json_list = [e.model_dump_json(exclude_none=True) for e in entities]
            passage = self._build_bilingual_passage(src_content)

            json_str, usage, cost_usd = await self._extract_from_passage(passage, entity_json_list)

            total_cost_usd += cost_usd
            total_tokens += usage.total_tokens
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens
            num_processed += 1

            result_dict = json.loads(json_str)
            result_dict[DBFields.KEY] = src_content.key

            out_path = os.path.join(
                self._get_output_dir(), src_content.key.replace(":", ";")
            )
            entities_block = "\n".join(entity_json_list)
            output_text = (
                f"COST: Tokens: Total={usage.total_tokens} approx cost=${cost_usd:.6f} "
                f"(Prompt={usage.input_tokens}, Completion={usage.output_tokens})\n"
                f"SOURCE:\n{src_content}\n\n"
                f"ENTITIES TO ENRICH ({len(entities)}):\n{entities_block}\n\n"
                f"PASSAGE:\n{passage}\n\n"
                f"EXTRACTED (JSON):\n{json_str}"
            )
            LocalPrinter.print_to_file(result_dict, FileTypeEnum.FileType.JSON, out_path)
            LocalPrinter.print_to_file(output_text, FileTypeEnum.FileType.TXT, out_path)

        print(f"\n{'='*60}")
        print(f"PROCESSED: {num_processed} sources, SKIPPED (no entities to enrich): {num_skipped}")
        print(
            f"TOTAL: {total_tokens} tokens "
            f"(prompt={total_input_tokens}, completion={total_output_tokens}), "
            f"${total_cost_usd:.6f} USD"
        )
        print(f"Results saved to: {self._get_output_dir()}")
        print(f"{'='*60}")

    # --- Enrichment helpers ---------------------------------------------------

    def _get_unenriched_entities_for_source(self, source_key: str) -> List[Entity]:
        """
        Look up the entities linked to *source_key* via SourceMetadata.entity_keys,
        and return only those that do NOT already have metadata (Entity.has_metadata).
        """
        src_metadata = self.db_api.get_source_metadata_by_key(source_key)
        if src_metadata is None or not src_metadata.entity_keys:
            return []

        entities = self.db_api.get_entities_by_keys(list(src_metadata.entity_keys))
        return [entity for entity in entities if not entity.has_metadata()]

    @staticmethod
    def _build_bilingual_passage(src_content: SourceContent) -> str:
        """Combine the clean English text and clean Hebrew (no niqqud) text of a source."""
        return (
            f"ENGLISH:\n{src_content.get_clean_en_text()}\n\n"
            f"HEBREW:\n{src_content.get_clean_heb_text()}"
        )


