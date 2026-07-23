# bs"d
import asyncio
from html import escape
import json
import os
from abc import abstractmethod
from typing import Any, List, Optional, Tuple

from backend.db.data_names.Books import Books
from backend.db.DBConstants import DBFields
from backend.common import Paths
from backend.file_utils import FileTypeEnum, OsFunctions
from backend.models_db.SourceClasses.SectionSorting import source_entry_sort_key
from backend.models_db.SourceClasses.SourceContent import SourceContent
from backend_pipeline.data_pipeline.DBScriptParentClass import DBParentClass
from backend_pipeline.file_utils_pipeline import LocalPrinter
from backend_pipeline.file_utils_pipeline.JsonUtils import JsonUtils


class DBPopulateLlmBase(DBParentClass):
    """
    Abstract base class for LLM-driven DB populator scripts.

    Provides the shared two-phase scaffold:
      Phase 1 — iterate all sources for a book, call the LLM once per source
                 (no retries), write JSON + TXT output files to _get_output_dir().
      Phase 2 — read those JSON files, parse each entry, and populate the DB.

    Subclasses must implement:
      _get_output_dir()        → directory where JSON output is written / read from
      _extract_from_passage()  → call the appropriate LLM agent for one passage
      _process_json_entries()  → parse JSON entries and write results to the DB

    Typical subclass setUp pattern:
        def setUp(self):
            super().setUp()
            ModelConfig.set_provider(ModelProvider.GEMINI_FREE)
            self.my_caller = MyCaller()
    """

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    # ─── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def _get_output_dir(self) -> str:
        """Return the directory where extracted JSON files are written and read from."""
        ...

    @abstractmethod
    async def _extract_from_passage(
        self, passage: str, entity_json_list: Optional[List[str]] = None
    ) -> Tuple[str, Any, float]:
        """
        Call the LLM for a single passage; return (json_str, usage, cost_usd).
        *usage* must expose .total_tokens, .input_tokens, .output_tokens.
        *entity_json_list* is an optional list of JSON strings (one per DB entity)
        that subclasses may use to give the LLM additional context — e.g. entities
        already found for this passage that still need metadata enrichment.
        Single attempt — no retries.
        """
        ...

    @abstractmethod
    def _process_json_entries(self, json_entries: List[Tuple[str, dict]]) -> None:
        """Parse loaded JSON entries [(source_key, data), ...] and write results to the DB."""
        ...

    # ─── Phase 1: LLM extraction → JSON files ─────────────────────────────────

    def test_run_extraction(self) -> None:
        """Entry point: clear output dir, then run LLM extraction for all sources."""
        OsFunctions.clear_create_directory(self._get_output_dir())
        asyncio.run(self._extract_all_to_json())

    def test_print_examples_src_contents_to_html(self) -> None:
        """Print example source contents to HTML files for visual inspection."""
        output_dir = os.path.join(Paths.TESTS_DIR, "source_content_examples")
        OsFunctions.clear_create_directory(output_dir)
        self._print_src_contents_to_html(get_examples_src_contents(self.db_api), output_dir)

    def _print_src_contents_to_html(
        self, src_contents: list[SourceContent], output_dir: str
    ) -> None:
        """
        Iterate source contents and print their HTML + clean text variants as HTML files.
        Raw HTML content is embedded directly so it renders nicely in a browser.
        """
        for src in src_contents:
            out_path = os.path.join(output_dir, src.key.replace(":", ";"))
            html_content = self._src_content_debug_html(src)
            LocalPrinter.print_to_file(html_content, FileTypeEnum.FileType.HTML, out_path)

        print(f"Source content HTML files saved to: {output_dir}")

    @staticmethod
    def _src_content_debug_html(src: SourceContent) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{escape(src.key)}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.5;
            margin: 24px;
        }}
        section {{
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 24px;
            padding: 16px;
        }}
        h1, h2 {{
            margin-top: 0;
        }}
        .hebrew {{
            direction: rtl;
            text-align: right;
        }}
        .clean-text {{
            background: #f8f8f8;
            border-radius: 6px;
            padding: 12px;
            white-space: pre-wrap;
        }}
        .raw-text {{
            font-family: "Courier New", Courier, monospace;
            white-space: pre-wrap;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <h1>{escape(src.key)}</h1>

    <section>
        <h2>src.get_heb_html_content()</h2>
        <div class="hebrew">{src.get_heb_html_content()}</div>
    </section>

    <section>
        <h2>src.get_clean_heb_text()</h2>
        <div class="hebrew clean-text">{escape(src.get_clean_heb_text())}</div>
    </section>

    <section>
        <h2>src.get_en_html_content()</h2>
        <div>{src.get_en_html_content()}</div>
    </section>

    <section>
        <h2>src.get_clean_en_text() (RAW repr — not rendered)</h2>
        <pre class="clean-text raw-text">{escape(repr(src.get_clean_en_text()))}</pre>
    </section>
</body>
</html>"""

    async def _extract_all_to_json(self, book=Books.GENESIS) -> None:
        """
        Iterate all sources for *book*, call the LLM once per source,
        save JSON and TXT files under _get_output_dir().
        """
        total_cost_usd = 0.0
        total_tokens = total_input_tokens = total_output_tokens = 0

        contents = self.db_api.get_all_src_contents_by_book(book)
        for src_content in contents:
            passage = src_content.get_clean_en_text()
            json_str, usage, cost_usd = await self._extract_from_passage(passage)

            total_cost_usd += cost_usd
            total_tokens += usage.total_tokens
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens

            result_dict = json.loads(json_str)
            result_dict[DBFields.KEY] = src_content.key

            out_path = os.path.join(
                self._get_output_dir(), src_content.key.replace(":", ";")
            )
            output_text = (
                f"COST: Tokens: Total={usage.total_tokens} approx cost=${cost_usd:.6f} "
                f"(Prompt={usage.input_tokens}, Completion={usage.output_tokens})\n"
                f"SOURCE:\n{src_content}\n\n"
                f"HEBREW:\n{src_content.get_clean_heb_text()}\n\n"
                f"ENGLISH:\n{passage}\n\n"
                f"EXTRACTED (JSON):\n{json_str}"
            )
            LocalPrinter.print_to_file(result_dict, FileTypeEnum.FileType.JSON, out_path)
            LocalPrinter.print_to_file(output_text, FileTypeEnum.FileType.TXT, out_path)

        print(f"\n{'='*60}")
        print(
            f"TOTAL: {total_tokens} tokens "
            f"(prompt={total_input_tokens}, completion={total_output_tokens}), "
            f"${total_cost_usd:.6f} USD"
        )
        print(f"Results saved to: {self._get_output_dir()}")
        print(f"{'='*60}")

    # ─── Phase 2: JSON files → DB ─────────────────────────────────────────────

    def test_populate_from_jsons(self) -> None:
        """Entry point: load JSON files from output dir and populate the DB."""
        json_entries = JsonUtils.read_jsons_from_dir_with_keys(self._get_output_dir())
        if not json_entries:
            print("No JSON files found in directory.")
            return
        json_entries.sort(key=source_entry_sort_key)
        print(f"Loaded {len(json_entries)} JSON files, sorted by source key.")
        self._process_json_entries(json_entries)


def get_examples_src_contents(db_api) -> list[SourceContent]:

    key_strs = [

        # person used as example (Reuven and shimon, yaakov in yerusha)
        # this case is not a concern... couldnt find passage of the gemara that have this phenomenom.. only in rishonim "BT_Bava Batra_0_116a:16-116b:3"

        # childofFather (levi)
        # 'TN_Exodus_0_6:14-25',

        # childOfMother
        # "TN_I Kings_0_2:13–3:2",

        # descendantOf
        'BT_Sanhedrin_0_96b:2-9',

        # spouseOf
        # 'TN_Genesis_0_30:3-8',

        # studiedFrom
        'BT_Eruvin_0_45a:12-19', # doesnt catch the second 'studied from!'
        # x said in name of y said in name of z.
        'BT_Berakhot_0_35b:11-12', # missing childOf
        "TN_Esther_0_1:1–22", # ensure no studied from! # also number

        # placeToNation (seir to edom)
        'TN_Genesis_0_36:1-19', # bad studied from - esav not studied from yaakov!. missed alias..

        # personBelongsToNation
        'BT_Sanhedrin_0_94a:4-10', # bad alias, (should be comparison..)

        # comparedTo
        'TN_Isaiah_0_1:1-31',
        "BT_Sanhedrin_0_105a:7-105b:1", # comparedTo, allyOf...

        # contrastedWith, non literal places (world to come vs this world) - ensure rav no prophesying
        'BT_Berakhot_0_17a:7-12',

        # AllyOf (person - person) also numbers
        'TN_I Kings_0_5:15–32',

        # bornIn
        'TN_Genesis_0_41:47-53',

        # visited
        'TN_Genesis_0_33:18-34:1', # also place to Nation

        # prayedAt
        "BT_Pesachim_0_88a:3-5",

        # enemyOF (nation to nation) - very long source
        'TN_II Kings_0_23:31–25:7', #todo include validation in pydatic!!
        #
        # diedIn (debora)
        "TN_Genesis_0_35:1-9",

        # personToTribeOfIsrael, also same person appearing with diff spelling (hege and hegai)
        "TN_Esther_0_2:1–20",

        # bat kol, beit shamai bet hillel (groups)
        "BT_Eruvin_0_13b:10-14",

    #     black garments (symbol), am haaretz
        'BT_Shabbat_0_114a:5-9',

    #     symbol - torah scroll
        'BT_Sanhedrin_0_67b:22-68a:12',

    #     symbol and compared to - the torah scroll and r eliezer
        'BT_Sotah_0_49b:15-19',

        # number
        "TN_II Kings_0_14:1–22",

        # food - quail (food and animal)
        "BT_Yoma_0_75a:19-75b:8",

        # animal - re'em
        "BT_Gittin_0_68a:5-68b:20",
        # animal speaking
        "BT_Gittin_0_45a:18-22",

        # plant , carob ( = food), sycamore (not food)
        "BT_Bava Batra_0_70a:2-7",


    ]
    res = [db_api.find_one_source_content(k) for k in key_strs]
    return res