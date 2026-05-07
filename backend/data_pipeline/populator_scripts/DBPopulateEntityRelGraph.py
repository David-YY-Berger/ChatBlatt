# bs'd
import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple

from backend.db.data_names.Books import Books
from backend.models.SourceClasses.SourceContent import SourceContent
from backend.models.SourceClasses.SectionSorting import source_entry_sort_key
from backend.models.EntityObjects.Entity import Entity
from backend.models.EntityObjects.EntityIdentity import PersonFamilyContext
from backend.models.Rel import Rel
from backend.models.Enums import EntityType, RelType
from backend.db.DBConstants import DBFields
from backend.data_pipeline.DBScriptParentClass import DBParentClass
from backend.data_pipeline.EntityRelManager import EntityRelManager
from backend.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
from backend.data_pipeline.llm_api.PydanticCaller import PydanticCaller
from backend.file_utils import LocalPrinter, FileTypeEnum, OsFunctions
from backend.file_utils.JsonUtils import JsonUtils
from backend.common import Paths


# Mapping from JSON category name -> EntityType enum
_CATEGORY_TO_ENTITY_TYPE: Dict[str, EntityType] = {et.description: et for et in EntityType}

# Mapping from JSON rel field name -> RelType enum
_REL_NAME_TO_REL_TYPE: Dict[str, RelType] = {rt.description: rt for rt in RelType}


class DBPopulateLmmData(DBParentClass):

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

        self.pydantic_caller = PydanticCaller()
        self.entity_rel_mngr = EntityRelManager()

    def tearDown(self):
        super().tearDown()

    ############################################## Populating Entities and Relationships ###############################################

    def test_async_run(self): # used to call Pydantic funcs..
        OsFunctions.clear_create_directory(Paths.LMM_RESPONSES_OUTPUT_DIR)
        # Run the entire batch as one async task
        # asyncio.run(self.test_populate_source_meta_data())
        asyncio.run(self.print_graphs_to_json())

    def test_populate_entities_and_rels_from_jsons(self):
        """
        Transactional: reads JSON files from a directory, extracts entities and relationships,
        inserts them into the DB. If any part fails, all inserts are rolled back.
        """
        dir_path = r"C:\Users\U6072661\PycharmProjects\ChatBlatt\Examples\comparingLLms\Gemini 2.5 Flash"

        # 1. Read JSONs with source keys derived from filenames
        json_entries: List[Tuple[str, dict]] = JsonUtils.read_jsons_from_dir_with_keys(dir_path)
        if not json_entries:
            print("No JSON files found in directory.")
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
                print(f"  [{ent.entityType.description}] {ent.display_en_name} (key={ent.key})")

            print(f"\n{'='*60}")
            print(f"RELATIONSHIPS INSERTED/FOUND: {len(all_rels)}")
            print(f"{'='*60}")
            for rel in all_rels:
                print(f"  {rel.term1} --[{rel.rel_type.description}]--> {rel.term2} (key={rel.key})")

        except Exception as e:
            print(f"TRANSACTION FAILED - all changes rolled back: {e}")
            raise
        finally:
            session.end_session()

    def _process_json_entries(self, json_entries: List[Tuple[str, dict]]) -> Tuple[List[Entity], List[Rel]]:
        """
        Process all JSON entries: insert entities, then relationships.
        For Person entities, family context is extracted per-entry from the JSON
        and the DB is queried directly to check for existing matches.
        Returns (all_entities, all_rels) with keys populated.
        """
        all_entities, entity_key_map = self._insert_entities_from_entries(json_entries)
        all_rels = self._insert_rels_from_entries(json_entries, entity_key_map)
        return all_entities, all_rels

    def _insert_entities_from_entries(
        self, json_entries: List[Tuple[str, dict]]
    ) -> Tuple[List[Entity], Dict[tuple, str]]:
        """
        Pass 1: iterate all JSON entries, insert each unique entity into the DB.
        For Person entities, extracts family context from the current JSON entry's rels
        and passes it to the DB layer for dedup against existing DB records.
        Returns (all_entities, entity_key_map) where entity_key_map maps
        (name_lower, entity_type) -> db key.
        """
        all_entities: List[Entity] = []
        entity_key_map: Dict[tuple, str] = {}

        for source_key, data in json_entries:
            res = self._get_res(data)
            entities_dict = res.get("Entities", {})
            rels_dict = res.get("Rel", {})

            for category_name, entity_type in _CATEGORY_TO_ENTITY_TYPE.items():
                for entity_data in entities_dict.get(category_name) or []:
                    entity, was_new = self._try_insert_entity(
                        entity_data, entity_type, entity_key_map, rels_dict
                    )
                    if was_new:
                        all_entities.append(entity)

        print(f"  Entities pass complete: {len(all_entities)} unique entities.")
        return all_entities, entity_key_map

    def _try_insert_entity(self, entity_data: dict, entity_type: EntityType,
                           entity_key_map: Dict[tuple, str],
                           rels_dict: dict,
    ) -> Tuple[Optional[Entity], bool]:
        """
        Insert a single entity into the DB if it hasn't been seen yet.
        For Person entities, extracts family context from rels_dict and passes it
        to the DB layer so it can check against existing DB records.
        Returns (entity, was_new). was_new=False means it was already in entity_key_map.
        """
        en_name = entity_data.get("en_name", "").strip()
        if not en_name:
            return None, False

        entity = Entity.create_from_en_name(en_name, entity_type)
        lookup_key = (en_name.lower(), entity_type)

        if lookup_key in entity_key_map:
            return None, False  # already processed in this batch

        # For Person entities, build family context from the JSON rels
        person_family = None
        if entity_type == EntityType.EPerson:
            person_family = self._extract_person_family_from_rels(en_name, rels_dict)

        entity.key = self.db_api.try_insert_entity(entity, person_family)
        entity_key_map[lookup_key] = entity.key
        return entity, True

    @staticmethod
    def _extract_person_family_from_rels(person_name: str, rels_dict: dict) -> PersonFamilyContext:
        """
        Extract family context (fathers, mothers, spouses) for a specific person
        from the current JSON entry's relationship data.
        """
        ctx = PersonFamilyContext()
        name_lower = person_name.lower()

        for rel_field_name, rel_list in rels_dict.items():
            if not rel_list:
                continue
            field_lower = rel_field_name.lower()

            for relation_data in rel_list:
                term1 = relation_data.get("term1", "").strip()
                term2 = relation_data.get("term2", "").strip()
                if not term1 or not term2:
                    continue

                if field_lower == "childoffather" and term1.lower() == name_lower:
                    ctx.fathers.add(term2.lower())
                elif field_lower == "childofmother" and term1.lower() == name_lower:
                    ctx.mothers.add(term2.lower())
                elif field_lower == "spouseof":
                    if term1.lower() == name_lower:
                        ctx.spouses.add(term2.lower())
                    elif term2.lower() == name_lower:
                        ctx.spouses.add(term1.lower())

        return ctx

    def _insert_rels_from_entries(
        self,
        json_entries: List[Tuple[str, dict]],
        entity_key_map: Dict[tuple, str],
    ) -> List[Rel]:
        """
        Pass 2: iterate all JSON entries, insert each relationship into the DB.
        Relies on entity_key_map built in Pass 1 to resolve entity names to keys.
        """
        all_rels: List[Rel] = []

        for source_key, data in json_entries:
            res = self._get_res(data)
            rels_dict = res.get("Rel", {})
            if not rels_dict:
                continue
            entities_dict = res.get("Entities", {})

            for rel_field_name, rel_list in rels_dict.items():
                rel_type = self._resolve_rel_type(rel_field_name, source_key)
                if rel_type is None or not rel_list:
                    continue

                for relation_data in rel_list:
                    rel = self._try_insert_rel(
                        relation_data, rel_type, rel_field_name, source_key,
                        entities_dict, entity_key_map
                    )
                    if rel is not None:
                        all_rels.append(rel)

        print(f"  Relationships pass complete: {len(all_rels)} relationships.")
        return all_rels

    def _try_insert_rel(
        self,
        relation_data: dict,
        rel_type: RelType,
        rel_field_name: str,
        source_key: str,
        entities_dict: dict,
        entity_key_map: Dict[tuple, str],
    ) -> Optional[Rel]:
        """
        Insert a single relationship into the DB.
        Returns the Rel on success, or None if entity names could not be resolved.
        """
        term1_name = relation_data.get("term1", "").strip()
        term2_name = relation_data.get("term2", "").strip()
        if not term1_name or not term2_name:
            return None

        term1_key = self._resolve_entity_key(term1_name, entities_dict, entity_key_map)
        term2_key = self._resolve_entity_key(term2_name, entities_dict, entity_key_map)

        if not term1_key or not term2_key:
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
        rel_type = _REL_NAME_TO_REL_TYPE.get(rel_field_name)
        if rel_type is None:
            rel_type = next(
                (rt for name, rt in _REL_NAME_TO_REL_TYPE.items()
                 if name.lower() == rel_field_name.lower()),
                None,
            )
        if rel_type is None:
            print(f"  WARNING: Unknown rel type '{rel_field_name}' in source {source_key}, skipping.")
        return rel_type

    def _resolve_entity_key(self, en_name: str, entities_dict: dict,
        entity_key_map: Dict[tuple, str]) -> Optional[str]:
        """
        Resolve an entity name to its key by checking which category it belongs to
        in the entities_dict, then looking up in entity_key_map using (name_lower, entity_type).
        """
        name_lower = en_name.lower()

        # Search through all categories to find what type this entity is
        for category_name, entity_type in _CATEGORY_TO_ENTITY_TYPE.items():
            entity_list = entities_dict.get(category_name, [])
            if not entity_list:
                continue
            for entity_data in entity_list:
                if entity_data.get("en_name", "").strip().lower() == name_lower:
                    lookup = (name_lower, entity_type)
                    if lookup in entity_key_map:
                        return entity_key_map[lookup]

        # Fallback: try all types
        for entity_type in EntityType:
            lookup = (name_lower, entity_type)
            if lookup in entity_key_map:
                return entity_key_map[lookup]
        # Fallback: scan all keys for matching name
        for key_tuple, db_key in entity_key_map.items():
            if key_tuple[0] == name_lower:
                return db_key

        return None

    ############################################## Print Graphs to JSON ###############################################

    async def print_graphs_to_json(self):
        # todo get the references of a passage too!

        total_cost_usd = 0.0
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0

        # contents = self.get_examples_src_contents()
        contents = self.db_api.get_all_src_contents_by_book(Books.GENESIS)
        for src_content in contents:
            passage = src_content.get_clean_en_text()

            graph_json_str, usage, cost_usd = await self.pydantic_caller.extract_graph_from_passage(passage)

            # Accumulate totals
            total_cost_usd += cost_usd
            total_tokens += usage.total_tokens
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens

            cost_summary = (
                f"Tokens: Total={usage.total_tokens} approx cost usd = ${cost_usd:.6f} "
                f"(Prompt={usage.input_tokens}, Completion={usage.output_tokens})"
            )
            # Add the src_key to the JSON
            graph_dict = json.loads(graph_json_str)
            graph_dict[DBFields.KEY] = src_content.key

            path = str(os.path.join(Paths.LMM_RESPONSES_OUTPUT_DIR, src_content.key.replace(':', ';')))

            output_text = (
                f"COST: {cost_summary}\n"
                f"SOURCE:\n{src_content}\n\n"
                f"HEBREW:\n{src_content.get_clean_heb_text()}\n\n"
                f"ENGLISH:\n{passage}\n\n"
                f"EXTRACTED GRAPH (JSON):\n{graph_json_str}"
            )

            LocalPrinter.print_to_file(
                graph_dict,  # Pass dict directly - LocalPrinter handles JSON formatting
                # FileTypeEnum.FileType.TXT,
                FileTypeEnum.FileType.JSON,
                path
            )
            LocalPrinter.print_to_file(
                output_text,
                FileTypeEnum.FileType.TXT,
                # FileTypeEnum.FileType.JSON,
                path
            )

        print(f"\n{'='*60}")
        print(f"TOTAL COST SUMMARY:")
        print(f"  Total Tokens: {total_tokens} (Prompt={total_input_tokens}, Completion={total_output_tokens})")
        print(f"  Total Cost: ${total_cost_usd:.6f} USD")
        print(f"{'='*60}")
        print(f"Results saved to: {Paths.LMM_RESPONSES_OUTPUT_DIR}")

    ############################################## Populating Metadata ###############################################

    async def test_populate_source_meta_data(self):

        print("Starting to populate source meta data.")
        all_srcs = self.db_api.get_all_src_contents_by_book(Books.GENESIS)
        # src_processed = 0
        # num_srcs_to_process = 20
        #
        # for src in all_srcs:
        #     if src_processed >= num_srcs_to_process:
        #         break
        #
        #     if self.db_api.is_src_metadata_exist(src.key):
        #         continue
        #
        #     analyzed_response = self.lmm_caller.analyze_src(src.content[SourceContentType.EN])
        #     src_metadata = SourceMetadata(key = src.key, source_type=src.source_type)
        #     src_metadata.passage_types = analyzed_response.e_passage_types
        #     src_metadata.summary_en = analyzed_response.summary_en
        #     src_metadata.summary_heb = analyzed_response.summary_heb
        #
        #     entity_keys = self.entity_rel_mngr.insert_entity_map(analyzed_response.get_entity_map(), src.get_src_type())
        #     src_metadata.entities.update(entity_keys)
        #
        #     rel_keys = self.entity_rel_mngr.insert_rel_map(analyzed_response.get_all_relationships(), src.get_src_type())
        #     src_metadata.entities.update(rel_keys)
        #
        #     is_success = self.db_api.insert_or_update_source_metadata(src)
        #     if is_success:
        #         src_processed += 1
        return

    ############################################## helper methods ####################################################
    def get_examples_src_contents(self) -> list[SourceContent]:
        # took sources from file:///C:/Users/U6072661/AppData/Local/Chatblatt/Tests/Questions/fight.html

        key_strs = [

            # person used as example (Reuven and shimon, yaakov in yerusha)
            # this case is not a concern... couldnt find passage of the gemara that have this phenomenom.. only in rishonim "BT_Bava Batra_0_116a:16-116b:3"

            # childofFather (levi)
            # 'TN_Exodus_0_6:14-25',

            # childOfMother
            # "TN_I Kings_0_2:13–3:2",

            # descendantOf
            # 'BT_Sanhedrin_0_96b:2-9',

            # spouseOf
            # 'TN_Genesis_0_30:3-8',

            # studiedFrom
            # 'BT_Eruvin_0_45a:12-19', # doesnt catch the second 'studied from!'
            # x said in name of y said in name of z.
            # 'BT_Berakhot_0_35b:11-12', # missing childOf
            "TN_Esther_0_1:1–22", # ensure no studied from! # also number

            # placeToNation (seir to edom)
            # 'TN_Genesis_0_36:1-19', # bad studied from - esav not studied from yaakov!. missed alias..

            # personBelongsToNation
            # 'BT_Sanhedrin_0_94a:4-10', # bad alias, (should be comparison..)

            # comparedTo
            # 'TN_Isaiah_0_1:1-31',
            # "BT_Sanhedrin_0_105a:7-105b:1", # comparedTo, allyOf...

            # contrastedWith, non literal places (world to come vs this world) - ensure rav no prophesying
            # 'BT_Berakhot_0_17a:7-12',

            # AllyOf (person - person) also numbers
            # 'TN_I Kings_0_5:15–32',

            # bornIn
            # 'TN_Genesis_0_41:47-53',

            # visited
            # 'TN_Genesis_0_33:18-34:1', # also place to Nation

            # prayedAt
            # "BT_Pesachim_0_88a:3-5",

            # enemyOF (nation to nation) - very long source
            # 'TN_II Kings_0_23:31–25:7', #todo include validation in pydatic!!
            #
            # diedIn (debora)
            # "TN_Genesis_0_35:1-9",

            # personToTribeOfIsrael, also same person appearing with diff spelling (hege and hegai)
            # "TN_Esther_0_2:1–20",

            # bat kol, beit shamai bet hillel (groups)
            # "BT_Eruvin_0_13b:10-14",

        #     black garments (symbol), am haaretz
        #     'BT_Shabbat_0_114a:5-9',

        #     symbol - torah scroll
        #     'BT_Sanhedrin_0_67b:22-68a:12',

        #     symbol and compared to - the torah scroll and r eliezer
        #     'BT_Sotah_0_49b:15-19',

            # number
            # "TN_II Kings_0_14:1–22",

            # food - quail (food and animal)
            # "BT_Yoma_0_75a:19-75b:8",

            # animal - re'em
            # "BT_Gittin_0_68a:5-68b:20",
            # animal speaking
            # "BT_Gittin_0_45a:18-22",

            # plant , carob ( = food), sycamore (not food)
            # "BT_Bava Batra_0_70a:2-7",


        ]
        res = [self.db_api.find_one_source_content(k) for k in key_strs]
        return res












