# bs'd
import asyncio
import json
import os

from backend.models.SourceClasses.SourceContent import SourceContent
from backend.db.Collections import CollectionObjs
from backend.db.DBConstants import DBFields
from backend.data_pipeline.DBScriptParentClass import DBParentClass
from backend.data_pipeline.EntityRelManager import EntityRelManager
from backend.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
from backend.data_pipeline.llm_api.PydanticCaller import PydanticCaller
from backend.file_utils import LocalPrinter, FileTypeEnum, OsFunctions
from backend.common import Paths


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

    def test_async_run(self):
        OsFunctions.clear_create_directory(Paths.LMM_RESPONSES_OUTPUT_DIR)
        # Run the entire batch as one async task
        asyncio.run(self.get_graphs_from_passages())

    async def get_graphs_from_passages(self):
        # todo get the references of a passage too!

        total_cost_usd = 0.0
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0

        for src_content in self.get_examples_src_contents():
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

    def test_populate_source_meta_data(self):
        pass
        all_srcs = self.db_api.get_all_src_contents_of_collection(CollectionObjs.TN)
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












