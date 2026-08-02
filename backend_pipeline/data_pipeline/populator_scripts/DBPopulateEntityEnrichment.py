# bs"d
"""
DBPopulateEntityEnrichment - Enrich existing entities with attributes derived from passages.

Two-phase workflow (inherited from DBPopulateLlmBase, driven by test_run_extraction_and_population):
  Phase 1 (_extract_all_to_json): iterate sources -> call LLM -> save JSON files.
    Each source is fully handled before moving to the next one: get content,
    call the LLM, then immediately populate/update the DB for that source.
    This ensures that if the same entity is linked to multiple sources, later
    sources in the same run already see it as enriched (Entity.has_metadata())
    and won't re-send it to the LLM.
  Phase 2 (test_populate_from_jsons): load ALL JSON files from the output dir and
    (re-)apply them to the DB. Since Phase 1 already persisted each source as it
    was processed, this pass is idempotent — it just confirms/re-syncs, acting as
    a safety net (e.g. useful if you only want to (re)run population from
    previously-generated JSON files without calling the LLM again).

For each source, the LLM is given a passage (clean English + clean Hebrew, no vowels)
plus the JSON of any associated entities (Person/Number/Place/Symbol, ...) that have not
yet been enriched. Each JSON file contains an EnrichmentResponse (entities: [...]) keyed
by entity 'key', filling in fields like display_heb_name, Person.timePeriod/isWoman/
isNonJew/isGroup/roles, Number.heb_unit/heb_context, Place.placeType, Symbol.symbolType.
Each entry is resolved back to a DB entity by key and patches its fields.
"""

import json
import os
from typing import List, Optional, Tuple
from types import SimpleNamespace

from backend.common import Paths
from backend.db.DBConstants import DBFields
from backend.db.data_names.Books import Books
from backend.file_utils import FileTypeEnum
from backend.models_db.EntityObjects.ENumber import ENumber
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.EntityObjects.EPerson import EPerson
from backend.models_db.EntityObjects.EPlace import EPlace
from backend.models_db.EntityObjects.ESymbol import ESymbol
from backend.models_db.Enums import EntityType, PlaceType, RoleType, SymbolType, TimePeriod
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend_pipeline.data_pipeline.llm_api.EntityEnrichmentCaller import EntityEnrichmentCaller, _match_enum_value
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
    #     be careful to put anything here! will be deleted...

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
        """
        Each entry is (source_key, data) where data == {"entities": [...], "key": source_key}
        (see EnrichmentResponse in EntityEnrichmentCaller). For every entity dict, resolve
        the matching DB entity by its 'key', patch in whichever enrichment fields are
        present (missing fields are simply left untouched), re-validating any enum-typed
        fields against the actual Python Enum values (values may have drifted since the
        JSON file was generated), then persist via EntityMongoMixin.update_entity.
        """
        num_updated = num_missing = num_unchanged = 0

        for source_key, data in json_entries:
            if not isinstance(data, dict):
                print(
                    f"  WARNING [{source_key}]: expected a dict with an 'entities' key but got "
                    f"{type(data).__name__}, skipping. (Is a non-enrichment JSON file sitting in "
                    f"{self._get_output_dir()}?)"
                )
                continue
            entity_dicts = data.get("entities") or []
            for entity_dict in entity_dicts:
                key = entity_dict.get(DBFields.KEY) or entity_dict.get("key")
                if not key:
                    print(f"  WARNING [{source_key}]: entity entry missing 'key', skipping: {entity_dict}")
                    continue

                entity = self.db_api.get_entity_by_key(key)
                if entity is None:
                    print(f"  WARNING [{source_key}]: no DB entity found for key '{key}', skipping.")
                    num_missing += 1
                    continue

                if self._apply_enrichment(entity, entity_dict, source_key):
                    self.db_api.update_entity(entity)
                    num_updated += 1
                else:
                    num_unchanged += 1

        print(f"\n{'='*60}")
        print(
            f"ENRICHMENT DB UPDATE: updated={num_updated}, "
            f"missing_entity={num_missing}, unchanged={num_unchanged}"
        )
        print(f"{'='*60}")

    @classmethod
    def _apply_enrichment(cls, entity: Entity, entity_dict: dict, source_key: str) -> bool:
        """
        Patch *entity* in place with whichever fields are present in *entity_dict*.
        Returns True if any field was actually changed.
        """
        changed = False

        heb_name = (entity_dict.get("display_heb_name") or "").strip()
        if heb_name and heb_name != entity.display_heb_name:
            entity.display_heb_name = heb_name
            changed = True

        if isinstance(entity, EPerson):
            changed = cls._apply_person_fields(entity, entity_dict, source_key) or changed
        if isinstance(entity, ENumber):
            changed = cls._apply_number_fields(entity, entity_dict) or changed
        if isinstance(entity, EPlace):
            changed = cls._apply_place_fields(entity, entity_dict, source_key) or changed
        if isinstance(entity, ESymbol):
            changed = cls._apply_symbol_fields(entity, entity_dict, source_key) or changed

        return changed

    @staticmethod
    def _apply_person_fields(entity: EPerson, entity_dict: dict, source_key: str) -> bool:
        changed = False

        raw_time_period = entity_dict.get("timePeriod")
        if raw_time_period:
            matched = _match_enum_value(raw_time_period, TimePeriod, f"timePeriod ({source_key})")
            if matched and entity.timePeriod != TimePeriod(matched):
                entity.timePeriod = TimePeriod(matched)
                changed = True

        for bool_field in ("isWoman", "isNonJew", "isGroup"):
            raw_value = entity_dict.get(bool_field)
            if isinstance(raw_value, bool) and getattr(entity, bool_field) != raw_value:
                setattr(entity, bool_field, raw_value)
                changed = True

        raw_roles = entity_dict.get("roles")
        if raw_roles:
            matched_roles = {
                RoleType(matched)
                for matched in (
                    _match_enum_value(raw_role, RoleType, f"roles ({source_key})") for raw_role in raw_roles
                )
                if matched
            }
            if matched_roles and not matched_roles.issubset(entity.roles):
                entity.roles = list(set(entity.roles) | matched_roles)
                changed = True

        return changed

    @staticmethod
    def _apply_number_fields(entity: ENumber, entity_dict: dict) -> bool:
        changed = False
        for field in ("heb_unit", "heb_context"):
            raw_value = (entity_dict.get(field) or "").strip()
            if raw_value and raw_value != getattr(entity, field):
                setattr(entity, field, raw_value)
                changed = True
        return changed

    @staticmethod
    def _apply_place_fields(entity: EPlace, entity_dict: dict, source_key: str) -> bool:
        raw_place_type = entity_dict.get("placeType")
        if not raw_place_type:
            return False
        matched = _match_enum_value(raw_place_type, PlaceType, f"placeType ({source_key})")
        if matched and entity.placeType != PlaceType(matched):
            entity.placeType = PlaceType(matched)
            return True
        return False

    @staticmethod
    def _apply_symbol_fields(entity: ESymbol, entity_dict: dict, source_key: str) -> bool:
        raw_symbol_type = entity_dict.get("symbolType")
        if not raw_symbol_type:
            return False
        matched = _match_enum_value(raw_symbol_type, SymbolType, f"symbolType ({source_key})")
        if matched and entity.symbolType != SymbolType(matched):
            entity.symbolType = SymbolType(matched)
            return True
        return False

    # --- Phase 1 override: custom source list + entity filtering --------------

    def test_run(self) -> None:
        self.test_run_extraction_and_population()

    async def _extract_all_to_json(self) -> None:
        """
        Iterate the example sources (get_examples_src_contents), and for each one:
          - look up its SourceMetadata to find linked entity keys
          - fetch those entities and drop any that already have metadata
          - if nothing is left to enrich, skip the source entirely (saves LLM calls)
          - otherwise call the LLM with the bilingual passage + remaining entities
          - immediately populate the DB with that source's enrichment result

        Sources are processed one at a time, fully, before moving to the next:
        get content -> populate metadata -> update DB -> next source. This matters
        because the same entity can be linked to multiple sources; persisting to the
        DB right away means that by the time a later source is processed,
        `_get_unenriched_entities_for_source` already sees the earlier update and
        won't re-send an already-enriched entity to the LLM.

        Saves JSON and TXT output files under _get_output_dir(), mirroring
        DBPopulateEntityRelGraph's Phase 1 output style.
        """
        total_cost_usd = 0.0
        total_tokens = total_input_tokens = total_output_tokens = 0
        num_processed = num_skipped = num_populate_failed = 0

        contents = get_examples_src_contents(self.db_api)
        # contents = self.db_api.get_all_src_contents_by_book(Books.GENESIS)
        for src_content in contents:
            entities = self._get_unenriched_entities_for_source(src_content.key)
            if not entities:
                print(f"  Skipping {src_content.key}: no entities need enrichment.")
                num_skipped += 1
                continue

            entity_json_list = [e.model_dump_json(exclude_none=True) for e in entities]
            passage = self._build_bilingual_passage(src_content)

            json_str, usage, cost_usd = await self._extract_from_passage(passage, entity_json_list)
            # cost_usd, json_str, usage = await self.temp_read_json_from_file() TEMP TESTING...

            total_cost_usd += cost_usd
            total_tokens += usage.total_tokens
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens
            num_processed += 1

            result_dict = json.loads(json_str)
            result_dict[DBFields.KEY] = src_content.key
            await self.add_display_en_name(entities, result_dict)

            # Populate the DB for THIS source right away, before moving to the next one.
            try:
                self._process_json_entries([(src_content.key, result_dict)])
            except Exception as e:
                print(f"  WARNING [{src_content.key}]: failed to populate DB for this source: {e}")
                num_populate_failed += 1

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

            # Debug-only dump of the (pre-enrichment) entity JSON list. This MUST NOT
            # live directly in _get_output_dir(): Phase 2 (test_populate_from_jsons)
            # scans every *.json file in that directory and expects each one to be a
            # dict shaped like {"entities": [...], "key": ...}. This dump is a plain
            # list of JSON strings, so writing it there previously caused
            # "'list' object has no attribute 'get'" once at least one source had
            # entities to enrich. Keep it in a subdirectory that Phase 2 never scans.
            debug_dir = os.path.join(self._get_output_dir(), "entity_lists_debug")
            os.makedirs(debug_dir, exist_ok=True)
            entity_list_out_path = os.path.join(
                debug_dir, f"{src_content.key.replace(':', ';')}_entity_json_list"
            )
            LocalPrinter.print_to_file(entity_json_list, FileTypeEnum.FileType.JSON, entity_list_out_path)
            LocalPrinter.print_to_file(entities_block, FileTypeEnum.FileType.TXT, entity_list_out_path)

        print(f"\n{'='*60}")
        print(
            f"PROCESSED: {num_processed} sources, SKIPPED (no entities to enrich): {num_skipped}, "
            f"DB POPULATE FAILURES: {num_populate_failed}"
        )
        print(
            f"TOTAL: {total_tokens} tokens "
            f"(prompt={total_input_tokens}, completion={total_output_tokens}), "
            f"${total_cost_usd:.6f} USD"
        )
        print(f"Results saved to: {self._get_output_dir()}")
        print(f"{'='*60}")

    async def add_display_en_name(self, entities, result_dict):
        entity_display_en_names_by_key = {entity.key: entity.display_en_name for entity in entities}
        for entity_dict in result_dict.get("entities") or []:
            entity_key = entity_dict.get(DBFields.KEY) or entity_dict.get("key")
            if entity_key in entity_display_en_names_by_key:
                entity_dict[DBFields.DISPLAY_EN_NAME] = entity_display_en_names_by_key[entity_key]

    async def temp_read_json_from_file(self):
        example_json_path = os.path.join(
            Paths.EXAMPLES_DIR,
            "entityEnrichment examples",
            "TN_Genesis_0_30;3-8.json",
        )
        with open(example_json_path, "r", encoding="utf-8-sig") as json_file:
            json_str = json_file.read()
        usage = SimpleNamespace(total_tokens=0, input_tokens=0, output_tokens=0)
        cost_usd = 0.0
        return cost_usd, json_str, usage

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
