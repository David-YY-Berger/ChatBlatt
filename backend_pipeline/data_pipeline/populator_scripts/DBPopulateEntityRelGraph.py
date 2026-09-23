# bs'd
from typing import Dict, List, Optional, Set, Tuple

from backend.db.data_names.Books import Books
from backend.models_db.SourceClasses.SectionSorting import source_entry_sort_key
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.EntityObjects.EntityIdentity import PassageRelation, PersonSourceContext
from backend.models_db.Rel import Rel
from backend.models_db.Enums import EntityType, RelType, PassageType
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend_pipeline.data_pipeline.populator_scripts.DBPopulateLlmBase import DBPopulateLlmBase
from backend.db.EntityRelManager import EntityRelManager
from backend_pipeline.data_pipeline.entity_resolution.PersonDisambiguator import PersonDisambiguator
from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
from backend_pipeline.data_pipeline.llm_api.EntityRelGraphCaller import EntityRelGraphCaller
from backend_pipeline.data_pipeline.PydanticModels.EntityIgnoreFilter import is_ignored_entity_name
from backend_pipeline.file_utils_pipeline.JsonUtils import JsonUtils
from backend.common import Paths


# Mapping from JSON category name -> EntityType enum
_CATEGORY_TO_ENTITY_TYPE: Dict[str, EntityType] = {et.value: et for et in EntityType}

# Mapping from JSON rel field name -> RelType enum
_REL_NAME_TO_REL_TYPE: Dict[str, RelType] = {rt.value: rt for rt in RelType}


def _lookup_rel_type(rel_field_name: str) -> Optional[RelType]:
    """RelType for a JSON rel field name (exact match first, then case-insensitive), or None."""
    rel_type = _REL_NAME_TO_REL_TYPE.get(rel_field_name)
    if rel_type is None:
        rel_type = next(
            (rt for name, rt in _REL_NAME_TO_REL_TYPE.items() if name.lower() == rel_field_name.lower()),
            None,
        )
    return rel_type


class DBPopulateEntityRelGraph(DBPopulateLlmBase):

    def setUp(self):
        """Runs before every test to set up directories and lazy init Faiss."""
        super().setUp()  # call parent setup first

        # ====== SWITCH MODEL HERE ======
        # Uncomment ONE of these lines to choose your model:

        # Standard modes (no extended thinking):
        ModelConfig.set_provider(ModelProvider.GEMINI_FREE)   # Gemini 2.5 Flash (free tier, rate limited)
        # ModelConfig.set_provider(ModelProvider.GEMINI_PAID)   # Gemini 2.5 Flash (paid tier)
        # ModelConfig.set_provider(ModelProvider.OPENAI)        # GPT-4o mini (paid)

        # Thinking modes (deeper reasoning, better for complex passages):
        # ModelConfig.set_provider(ModelProvider.GEMINI_FREE_THINKING)   # Flash + thinking (free tier)
        # ModelConfig.set_provider(ModelProvider.GEMINI_PAID_THINKING)   # Flash + thinking (paid tier)
        # ===============================

        self.pydantic_caller = EntityRelGraphCaller()
        self.entity_rel_mngr = EntityRelManager()
        self.person_disambiguator = PersonDisambiguator(self.db_api)

    def tearDown(self):
        super().tearDown()

    # ─── DBPopulateLlmBase abstract method implementations ────────────────────

    def _get_output_dir(self) -> str:
        return Paths.LMM_RESPONSES_OUTPUT_DIR

    async def _extract_from_passage(self, passage: str):
        return await self.pydantic_caller.extract_graph_from_passage(passage)

    # ─── Entry points ─────────────────────────────────────────────────────────

    def test_async_run(self):
        """Run LLM extraction for all sources → saves JSON files."""
        self.test_run_extraction_and_population()

    def test_populate_entities_and_rels_from_jsons(self):
        """
        Transactional: reads JSON files from a directory, extracts entities and relationships,
        inserts them into the DB. If any part fails, all inserts are rolled back.
        """
        # dir_path = Paths.TEST_DATA_BEREISHIT_ENTITY_REL_DIR
        dir_path = Paths.LMM_RESPONSES_OUTPUT_DIR

        # 1. Read JSONs with source keys derived from filenames
        json_entries: List[Tuple[str, dict]] = JsonUtils.read_jsons_from_dir_with_keys(dir_path)
        if not json_entries:
            print(f"No JSON files found in directory - {dir_path}")
            return

        # 2. Sort by source key using SourceClass sorting logic
        json_entries.sort(key=source_entry_sort_key)
        print(f"Loaded {len(json_entries)} JSON files, sorted by source key.")

        # 3. Transactional: use a MongoDB session with transaction
        session = self.db_api.client.start_session()
        try:
            with session.start_transaction():
                all_entities, all_rels = self._process_json_entries(json_entries)

            # Print results
            print(f"\n{'='*60}")
            print(f"ENTITIES INSERTED/FOUND: {len(all_entities)}")
            print(f"{'='*60}")
            for ent in all_entities:
                print(f"  [{ent.entityType.value}] {ent.display_en_name} (key={ent.key})")

            print(f"\n{'='*60}")
            print(f"RELATIONSHIPS INSERTED/FOUND: {len(all_rels)}")
            print(f"{'='*60}")
            for rel in all_rels:
                print(f"  {rel.term1} --[{rel.rel_type.value}]--> {rel.term2} (key={rel.key})")

        except Exception as e:
            print(f"TRANSACTION FAILED - all changes rolled back: {e}")
            raise
        finally:
            session.end_session()

    def _process_json_entries(self, json_entries: List[Tuple[str, dict]]) -> Tuple[List[Entity], List[Rel]]:
        """
        Processes the sources ONE AT A TIME, each one fully - entities, then relationships,
        then source metadata - before moving on to the next. Person disambiguation compares a
        mention with what the DB knows about each same-named candidate (its relationships and
        the sources mentioning it), so each source must see everything earlier sources wrote:
        e.g. a Person created by source 3 must already have its relationships in the DB when
        source 9 mentions someone with the same name.
        Returns (all_entities, all_rels) with keys populated; all_entities lists each resolved
        DB entity once.
        """
        all_entities: List[Entity] = []
        all_rels: List[Rel] = []
        ignored_entity_keys: Set[tuple] = set()
        seen_entity_db_keys: Set[str] = set()

        for source_key, data in json_entries:
            res = self._get_res(data)
            source_entity_map, source_entities = self._insert_entities_for_source(source_key, res, ignored_entity_keys)
            source_rels = self._insert_rels_for_source(source_key, res, source_entity_map, ignored_entity_keys)
            self._upsert_source_metadata_for_source(source_key, res, source_entity_map, {rel.key for rel in source_rels})

            for entity in source_entities:
                if entity.key not in seen_entity_db_keys:
                    seen_entity_db_keys.add(entity.key)
                    all_entities.append(entity)
            all_rels.extend(source_rels)

        print(f"  Processed {len(json_entries)} sources: {len(all_entities)} unique entities, "
              f"{len(all_rels)} relationships, {len(json_entries)} source metadata entries upserted.")
        if ignored_entity_keys:
            print(f"  Ignored {len(ignored_entity_keys)} non-proper-noun Person/Place entities.")
        return all_entities, all_rels

    def _insert_entities_for_source(
        self, source_key: str, res: dict, ignored_entity_keys: Set[tuple]
    ) -> Tuple[Dict[tuple, str], List[Entity]]:
        """
        Inserts (or finds) every entity mentioned in one source.
        Returns (source_entity_map, entities). source_entity_map maps each entity's identity
        tuple (name_lower, entity_type) -> DB key for THIS source only - the same name can
        resolve to different DB entities in different sources - and is what this source's
        relationships and metadata are resolved with. Entities dropped by the non-proper-noun
        filter are added to ignored_entity_keys, so relationships referencing them are skipped.
        """
        source_entity_map: Dict[tuple, str] = {}
        entities: List[Entity] = []
        entities_dict = res.get("Entities") or {}
        for category_name, entity_type in _CATEGORY_TO_ENTITY_TYPE.items():
            for entity_data in entities_dict.get(category_name) or []:
                entity = self._try_insert_entity(
                    source_key, res, entity_data, entity_type, source_entity_map, ignored_entity_keys
                )
                if entity is not None:
                    entities.append(entity)
        return source_entity_map, entities

    def _try_insert_entity(self, source_key: str, res: dict, entity_data: dict, entity_type: EntityType,
                           source_entity_map: Dict[tuple, str],
                           ignored_entity_keys: Set[tuple],
    ) -> Optional[Entity]:
        """
        Resolves one entity of this source to a DB key - inserting it if needed - and records
        it in source_entity_map. Person mentions go through PersonDisambiguator (different
        people can share a name); every other type is matched by name + type.
        Returns the entity (with its key), or None if skipped (no name, filtered out as a
        non-proper noun, or already resolved earlier in this source).
        """
        en_name = entity_data.get("en_name", "").strip()
        if not en_name:
            return None

        entity_class = Entity.get_class_for_type(entity_type)
        entity = entity_class.create_from_entity_data(entity_data, entity_type)
        lookup_key = entity.get_identity_tuple()

        # Deterministic post-processing filter: the LLM sometimes returns generic
        # nouns instead of proper nouns for Person/Place. Drop any entity whose
        # name contains (as a substring) a known non-proper-noun term, and record
        # its identity so relationships referencing it are skipped too.
        if is_ignored_entity_name(en_name, entity_type):
            ignored_entity_keys.add(lookup_key)
            print(f"  Skipping non-proper-noun {entity_type.value} entity: '{en_name}'")
            return None

        if lookup_key in source_entity_map:
            return None  # already resolved earlier in this same source

        if entity_type == EntityType.EPerson:
            person_ctx = self._build_person_source_context(source_key, en_name, res)
            existing_key = self.person_disambiguator.find_existing_person_key(entity, person_ctx)
            entity.key = existing_key or self.db_api.insert_entity(entity)
        else:
            entity.key = self.db_api.try_insert_entity(entity)

        source_entity_map[lookup_key] = entity.key
        return entity

    @staticmethod
    def _build_person_source_context(source_key: str, person_name: str, res: dict) -> PersonSourceContext:
        """
        Collects what this source says about one Person mention: its relationships (type,
        direction, other term) and the names of the other entities the source mentions.
        Entities dropped by the non-proper-noun filter are left out of both.
        """
        person = person_name.lower()

        kept_names: Set[str] = set()
        dropped_names: Set[str] = set()
        for category_name, entity_type in _CATEGORY_TO_ENTITY_TYPE.items():
            for entity_data in (res.get("Entities") or {}).get(category_name) or []:
                name = entity_data.get("en_name", "").strip()
                if name:
                    (dropped_names if is_ignored_entity_name(name, entity_type) else kept_names).add(name.lower())
        dropped_names -= kept_names

        relations: List[PassageRelation] = []
        for rel_field_name, rel_list in (res.get("Rel") or {}).items():
            rel_type = _lookup_rel_type(rel_field_name)
            if rel_type is None:
                continue
            for relation_data in rel_list or []:
                term1 = relation_data.get("term1", "").strip().lower()
                term2 = relation_data.get("term2", "").strip().lower()
                if term1 == person and term2 and term2 != person and term2 not in dropped_names:
                    relations.append(PassageRelation(rel_type, True, term2))
                elif term2 == person and term1 and term1 != person and term1 not in dropped_names:
                    relations.append(PassageRelation(rel_type, False, term1))

        return PersonSourceContext(
            source_key=source_key,
            relations=list(dict.fromkeys(relations)),
            source_entity_names=kept_names - {person},
        )

    def _insert_rels_for_source(self, source_key: str, res: dict, source_entity_map: Dict[tuple, str],
                                ignored_entity_keys: Set[tuple]) -> List[Rel]:
        """
        Inserts every relationship of one source, resolving entity names with this source's
        own entity map. Relationships referencing an entity dropped by the non-proper-noun
        filter are skipped.
        """
        rels: List[Rel] = []
        entities_dict = res.get("Entities") or {}
        for rel_field_name, rel_list in (res.get("Rel") or {}).items():
            rel_type = self._resolve_rel_type(rel_field_name, source_key)
            if rel_type is None or not rel_list:
                continue

            for relation_data in rel_list:
                rel = self._try_insert_rel(
                    relation_data, rel_type, rel_field_name, source_key,
                    entities_dict, source_entity_map, ignored_entity_keys
                )
                if rel is not None:
                    rels.append(rel)
        return rels

    def _upsert_source_metadata_for_source(self, source_key: str, res: dict, source_entity_map: Dict[tuple, str],
                                           rel_keys: Set[str]) -> None:
        """
        Builds this source's SourceMetadata (key, source_type, summary_en, summary_heb,
        passage_types, entity_keys, rel_keys) and upserts it into the DB.
        """
        src_metadata = SourceMetadata(key=source_key)
        src_metadata.summary_en = res.get("en_summary")
        src_metadata.summary_heb = res.get("heb_summary")
        src_metadata.passage_types = self._parse_passage_types(res.get("passage_types") or [])
        src_metadata.entity_keys = set(source_entity_map.values())
        src_metadata.rel_keys = rel_keys
        self.db_api.upsert_source_metadata(src_metadata)

    @staticmethod
    def _parse_passage_types(passage_type_strs: List[str]) -> List[PassageType]:
        """
        Convert LLM passage-type strings (e.g. "LAW", "STORY") to PassageType enum values.
        Matching is case-insensitive against both enum name and description.
        """
        _pt_map: Dict[str, PassageType] = {}
        for pt in PassageType:
            _pt_map[pt.name.upper()] = pt
            _pt_map[pt.value.upper()] = pt

        result: List[PassageType] = []
        for pt_str in passage_type_strs:
            pt = _pt_map.get(pt_str.upper())
            if pt is not None:
                result.append(pt)
            else:
                print(f"  WARNING: Unknown passage type '{pt_str}', skipping.")
        return result

    def _try_insert_rel(
        self,
        relation_data: dict,
        rel_type: RelType,
        rel_field_name: str,
        source_key: str,
        entities_dict: dict,
        source_entity_map: Dict[tuple, str],
        ignored_entity_keys: Set[tuple],
    ) -> Optional[Rel]:
        """
        Insert a single relationship into the DB.
        Returns the Rel on success, or None if entity names could not be resolved
        (or one of the terms refers to an entity that was deliberately filtered out
        by the non-proper-noun ignore list, in which case the relationship is
        silently dropped rather than treated as a resolution error).
        """
        term1_name = relation_data.get("term1", "").strip()
        term2_name = relation_data.get("term2", "").strip()
        if not term1_name or not term2_name:
            return None

        term1_key, term1_ignored = self._resolve_entity_key(term1_name, entities_dict, source_entity_map, ignored_entity_keys)
        term2_key, term2_ignored = self._resolve_entity_key(term2_name, entities_dict, source_entity_map, ignored_entity_keys)

        if not term1_key or not term2_key:
            if term1_ignored or term2_ignored:
                ignored_term = term1_name if term1_ignored else term2_name
                print(f"  Skipping relationship '{term1_name}' --[{rel_field_name}]--> '{term2_name}' "
                      f"in {source_key}: '{ignored_term}' was filtered as a non-proper-noun entity.")
            else:
                print(f"  WARNING: Could not resolve entities for rel "
                      f"'{term1_name}' --[{rel_field_name}]--> '{term2_name}' in {source_key}")
            return None

        rel = Rel.create(rel_type=rel_type, term1=term1_key, term2=term2_key)
        rel.key = self.db_api.try_insert_rel(rel)
        return rel

    @staticmethod
    def _get_res(data: dict) -> dict:
        """Unwrap {"res": ...} wrapper if present, otherwise return data as-is."""
        return data.get("res", data)

    @staticmethod
    def _resolve_rel_type(rel_field_name: str, source_key: str) -> Optional[RelType]:
        """
        Look up RelType by field name (exact match first, then case-insensitive).
        Prints a warning and returns None if the name is unrecognised.
        """
        rel_type = _lookup_rel_type(rel_field_name)
        if rel_type is None:
            print(f"  WARNING: Unknown rel type '{rel_field_name}' in source {source_key}, skipping.")
        return rel_type

    def _resolve_entity_key(self, en_name: str, entities_dict: dict,
        source_entity_map: Dict[tuple, str],
        ignored_entity_keys: Set[tuple]) -> Tuple[Optional[str], bool]:
        """
        Resolve an entity name to its key by checking which category it belongs to
        in the entities_dict, then looking up in this source's entity map
        (built for the same source in Pass 1).
        Each entity type uses its own identity tuple via create_from_entity_data + get_identity_tuple.

        Returns (key, was_ignored). was_ignored=True means the name matched an entity
        that was deliberately dropped by the non-proper-noun ignore filter (as opposed
        to a genuinely unresolvable name), so key is None but no warning should be logged.
        """
        name_lower = en_name.lower()
        matched_ignored = False

        # Primary: find this entity in the entities_dict so we can build its exact identity tuple
        for category_name, entity_type in _CATEGORY_TO_ENTITY_TYPE.items():
            entity_list = entities_dict.get(category_name, [])
            if not entity_list:
                continue
            for entity_data in entity_list:
                if entity_data.get("en_name", "").strip().lower() == name_lower:
                    entity_class = Entity.get_class_for_type(entity_type)
                    lookup = entity_class.create_from_entity_data(entity_data, entity_type).get_identity_tuple()
                    if lookup in source_entity_map:
                        return source_entity_map[lookup], False
                    if lookup in ignored_entity_keys:
                        matched_ignored = True

        # Fallback: try all types by default name-based key
        for entity_type in EntityType:
            lookup = (name_lower, entity_type)
            if lookup in source_entity_map:
                return source_entity_map[lookup], False
            if lookup in ignored_entity_keys:
                matched_ignored = True
        # Fallback: scan all keys for matching name
        for key_tuple, db_key in source_entity_map.items():
            if key_tuple[0] == name_lower:
                return db_key, False

        return None, matched_ignored



    ############################################## helper methods ####################################################












