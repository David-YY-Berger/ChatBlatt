# bs"d
import asyncio
import json
import os
from abc import abstractmethod
from typing import Any, List, Tuple

from backend.db.data_names.Books import Books
from backend.db.DBConstants import DBFields
from backend.common import Paths
from backend.file_utils import FileTypeEnum, OsFunctions
from backend.models_db.SourceClasses.SectionSorting import source_entry_sort_key
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
    async def _extract_from_passage(self, passage: str) -> Tuple[str, Any, float]:
        """
        Call the LLM for a single passage; return (json_str, usage, cost_usd).
        *usage* must expose .total_tokens, .input_tokens, .output_tokens.
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
