# bs"d
"""
EntityPipelineRunner - single clear place to run DBPopulateEntityRelGraph and/or
DBPopulateEntityEnrichment across one or more books, without opening either of those files
and editing their hardcoded setUp() params by hand.

This file does NOT reimplement any population/resolution logic. For every (book, step,
stage) it drives, it builds a real instance of the existing populator class and calls one
of its existing, already-tested public `test_*` methods - the exact same method you'd click
"Run" on in PyCharm. This runner only adds: looping over a book list, picking which method
to call, and printing a banner before each one so it's always obvious what's running.

Quick start - see the `if __name__ == "__main__":` block at the bottom of this file for a
ready-to-edit example. Typical usage:

    from backend_pipeline.data_pipeline.populator_scripts.EntityPipelineRunner import (
        EntityPipelineRunner, Stage, TANACH_BOOKS, BAVLI_BOOKS,
    )
    from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelProvider
    from backend.db.data_names.Books import Books

    runner = EntityPipelineRunner(
        books=[Books.GENESIS],              # or TANACH_BOOKS / BAVLI_BOOKS / a hand-picked list
        model_provider=ModelProvider.GEMINI_PAID,
        max_sources_per_book=None,          # None = whole book; set an int for a cheap smoke test
    )
    try:
        runner.preview_plan()               # prints the plan - no DB/LLM calls - sanity check first
        runner.run_full_pipeline()          # per book: rel-graph (both phases), then enrichment (both phases)
    finally:
        runner.close()                      # disconnect the shared DB connection, once, at the end

IMPORTANT (see control_docs/conventions/safety_and_testing.md): there is no separate test
DB. Every book processed here writes to the real, persistent DB UNLESS the step/stage
combination is DB-write-free (see the Stage enum docstring below for the one caveat on
ENTITY_ENRICHMENT + EXTRACT_ONLY).
"""

import unittest
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple, Type

from backend.db.data_names.Books import Book, Books
from backend.models_db.Enums import SourceType
from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider
from backend_pipeline.data_pipeline.populator_scripts.DBPopulateEntityEnrichment import DBPopulateEntityEnrichment
from backend_pipeline.data_pipeline.populator_scripts.DBPopulateEntityRelGraph import DBPopulateEntityRelGraph
from backend_pipeline.data_pipeline.populator_scripts.DBPopulateLlmBase import DBPopulateLlmBase


class Step(Enum):
    """Which populator to run."""
    ENTITY_REL_GRAPH = "entity_rel_graph"
    ENTITY_ENRICHMENT = "entity_enrichment"


class Stage(Enum):
    """
    Which part of a populator's two-phase scaffold to run for one book.

    EXTRACT_AND_POPULATE - both phases, chained (the normal/default case; same as clicking
        "Run" on test_async_run / test_run). Resumable - already-extracted sources are
        skipped (no LLM call), already-written entities/rels are found, not duplicated.
    EXTRACT_ONLY - phase 1 only (LLM -> JSON/TXT files), phase 2 deliberately not run.
        CAVEAT: for Step.ENTITY_ENRICHMENT this is NOT DB-write-free - that populator's
        phase 1 already writes each source's enrichment to the DB as it goes (see
        DBPopulateEntityEnrichment's module docstring) - there, EXTRACT_ONLY behaves
        identically to EXTRACT_AND_POPULATE. True "generate JSON, don't touch the DB yet"
        only applies to Step.ENTITY_REL_GRAPH.
    POPULATE_ONLY - phase 2 only: (re-)read whatever JSON files already sit in the book's
        output dir and write them to the DB. No LLM calls. Useful to re-apply after
        reviewing phase-1 output, or to re-sync after a DB reset without re-extracting.
    CLEAR_OUTPUT_DIR - wipe the book's output dir. Use before deliberately redoing every
        source from scratch (e.g. after a prompt change) - no DB writes.
    """
    EXTRACT_AND_POPULATE = "extract_and_populate"
    EXTRACT_ONLY = "extract_only"
    POPULATE_ONLY = "populate_only"
    CLEAR_OUTPUT_DIR = "clear_output_dir"


# (Step, Stage) -> name of the existing public test_* method that does exactly that.
# Every value here is a real, already-tested method on DBPopulateLlmBase or the named
# subclass - this runner never calls private/protected methods directly.
_STAGE_METHOD: Dict[Tuple[Step, Stage], str] = {
    (Step.ENTITY_REL_GRAPH, Stage.EXTRACT_AND_POPULATE): "test_async_run",
    (Step.ENTITY_REL_GRAPH, Stage.EXTRACT_ONLY): "test_run_extraction_only",
    (Step.ENTITY_REL_GRAPH, Stage.POPULATE_ONLY): "test_populate_entities_and_rels_from_jsons",
    (Step.ENTITY_REL_GRAPH, Stage.CLEAR_OUTPUT_DIR): "test_force_clear_output_dir",
    (Step.ENTITY_ENRICHMENT, Stage.EXTRACT_AND_POPULATE): "test_run",
    (Step.ENTITY_ENRICHMENT, Stage.EXTRACT_ONLY): "test_run_extraction_only",
    (Step.ENTITY_ENRICHMENT, Stage.POPULATE_ONLY): "test_populate_from_jsons",
    (Step.ENTITY_ENRICHMENT, Stage.CLEAR_OUTPUT_DIR): "test_force_clear_output_dir",
}

_STEP_CLASS: Dict[Step, Type[DBPopulateLlmBase]] = {
    Step.ENTITY_REL_GRAPH: DBPopulateEntityRelGraph,
    Step.ENTITY_ENRICHMENT: DBPopulateEntityEnrichment,
}

# Instance attribute each class's setUp() reads the book override from (see the
# getattr(self, ..., <default>) hooks added to both classes' setUp()).
_STEP_BOOK_ATTR: Dict[Step, str] = {
    Step.ENTITY_REL_GRAPH: "book_to_extract",
    Step.ENTITY_ENRICHMENT: "book_to_enrich",
}

# Instance attribute holding the LLM caller whose Gemini context-cache resource must be
# closed after each run (mirrors each class's own tearDown(), minus the DB disconnect -
# see EntityPipelineRunner._run_one for why that part is intentionally skipped here).
_STEP_CALLER_ATTR: Dict[Step, str] = {
    Step.ENTITY_REL_GRAPH: "pydantic_caller",
    Step.ENTITY_ENRICHMENT: "enrichment_caller",
}

# Convenience book lists, in canonical (book order) sequence - see Books.py / BookRegistry.
# NOTE: must call Books.by_source(...), not BookRegistry.by_source(...) directly -
# BookRegistry.all() reads cls.__dict__, which only holds the actual Book instances when
# cls is the Books subclass that defines them, not the BookRegistry base itself.
TANACH_BOOKS: List[Book] = Books.by_source(SourceType.TN)
BAVLI_BOOKS: List[Book] = Books.by_source(SourceType.BT)
# Tanach before Bavli: Bavli passages routinely reference Tanach figures/places, so
# processing Tanach first gives Person disambiguation more to work with when Bavli runs.
ALL_BOOKS: List[Book] = TANACH_BOOKS + BAVLI_BOOKS


@dataclass
class _BookRunResult:
    step: Step
    book: Book
    stage: Stage
    ok: bool
    error: Optional[str] = None


class EntityPipelineRunner:
    """
    Drives DBPopulateEntityRelGraph / DBPopulateEntityEnrichment across one or more books.
    See this module's top-of-file docstring for a usage example.
    """

    def __init__(
        self,
        books: Sequence[Book] = (),
        model_provider: ModelProvider = ModelProvider.GEMINI_PAID,
        max_sources_per_book: Optional[int] = None,
        use_examples: bool = False,
        json_only: bool = False,
        source_keys: Optional[Sequence[str]] = None,
    ):
        """
        source_keys: run ONLY these specific source keys (e.g. 'TN_Genesis_0_6:14-25')
            instead of whole books. The books are derived from the keys, so `books` may be
            omitted; if given too, `books` is ignored. Sources are processed per book (book
            order). Note rel-graph phase 1 skips a source whose JSON output already exists -
            delete that file (or use clear_output_dirs) to force a re-extract.
        books: the books to process, IN ORDER (e.g. TANACH_BOOKS, BAVLI_BOOKS, ALL_BOOKS,
            or a hand-picked list like [Books.GENESIS, Books.BERAKHOT]). Ignored when
            use_examples=True.
        model_provider: LLM provider/model used for every call this run makes.
        max_sources_per_book: caps each book to its first N sources (book order) - None
            (default) processes the whole book. Set an int for a cheap/quick smoke test
            across many books before committing to a full run.
        use_examples: run ONLY the passages listed in DBPopulateLlmBase.get_examples_src_contents
            (edit that list to choose them) instead of whole books. Runs once per step; output
            goes to a throwaway dir (Paths.get_examples_output_dir), cleared at the start of
            every extracting run so edited prompts/passages are never served from stale files.
        json_only: only call the LLM and write JSON/TXT files - never write to the DB.
            Rel-graph: stage EXTRACT_AND_POPULATE is downgraded to EXTRACT_ONLY. Enrichment:
            its per-source DB write is skipped (it still READS the DB for the entities to
            enrich, so it finds nothing for sources whose rel-graph hasn't been populated).
            Stages that don't extract (POPULATE_ONLY, CLEAR_OUTPUT_DIR) are unaffected.
        """
        self.books = list(books)
        self.model_provider = model_provider
        self.max_sources_per_book = max_sources_per_book
        self.use_examples = use_examples
        self.json_only = json_only
        self.source_keys_by_book: Dict[Book, List[str]] = {}
        if source_keys and not use_examples:
            self.source_keys_by_book = self._group_keys_by_book(source_keys)
            self.books = sorted(self.source_keys_by_book)
        if not use_examples and not self.books:
            raise ValueError("Pass books=[...], source_keys=[...] or use_examples=True.")
        self._initialized_classes: List[Type[DBPopulateLlmBase]] = []
        self.results: List[_BookRunResult] = []

    @staticmethod
    def _group_keys_by_book(source_keys: Sequence[str]) -> Dict[Book, List[str]]:
        """Key format '<SOURCE_TYPE>_<BookDatabaseName>_0_<ref>' -> {book: [keys]}."""
        grouped: Dict[Book, List[str]] = {}
        for key in dict.fromkeys(source_keys):
            parts = key.split("_")
            book = Books.get_by_db_name(parts[1]) if len(parts) > 2 else None
            if book is None or book.source_type.name != parts[0]:
                raise ValueError(f"Cannot resolve a book from source key: {key!r}")
            grouped.setdefault(book, []).append(key)
        return grouped

    def _targets(self) -> List[Optional[Book]]:
        """Books to iterate; examples mode is a single run with no book."""
        return [None] if self.use_examples else list(self.books)

    def _effective_stage(self, step: Step, stage: Stage) -> Stage:
        if self.json_only and stage == Stage.EXTRACT_AND_POPULATE:
            return Stage.EXTRACT_ONLY
        return stage

    # ─── Public entry points ───────────────────────────────────────────────

    def run_full_pipeline(
        self,
        rel_graph_stage: Stage = Stage.EXTRACT_AND_POPULATE,
        enrichment_stage: Stage = Stage.EXTRACT_AND_POPULATE,
        continue_on_error: bool = False,
    ) -> None:
        """
        For each book, in order: run DBPopulateEntityRelGraph (rel_graph_stage), THEN
        DBPopulateEntityEnrichment (enrichment_stage) for that SAME book, before moving to
        the next book. This order matters: DBPopulateEntityEnrichment only enriches entities
        already linked to a source via SourceMetadata.entity_keys, which is written by
        DBPopulateEntityRelGraph - running enrichment for a book before rel-graph has
        populated it finds nothing to enrich for every source (see control_docs/pipeline/
        population_pipeline_overview.md, "Run order").

        continue_on_error: if False (default), a failure stops the whole run immediately -
        the book/step/stage it happened on is printed, and re-running resumes cleanly
        (phase-1 output and DB writes already committed are not redone/duplicated). If True,
        a failed (book, step) is logged and skipped, and the run continues with the rest -
        useful for a long unattended run across all of Tanach/Bavli where you'd rather
        collect every failure than stop at the first one; check self.results afterwards.
        """
        for book in self._targets():
            self._run_one(Step.ENTITY_REL_GRAPH, book, rel_graph_stage, continue_on_error)
            self._run_one(Step.ENTITY_ENRICHMENT, book, enrichment_stage, continue_on_error)
        self._print_summary()

    def run_step(self, step: Step, stage: Stage = Stage.EXTRACT_AND_POPULATE,
                 continue_on_error: bool = False) -> None:
        """Run a single step (just rel-graph, or just enrichment) for every book, in order."""
        for book in self._targets():
            self._run_one(step, book, stage, continue_on_error)
        self._print_summary()

    def clear_output_dirs(self, step: Step) -> None:
        """Wipe every book's output dir for *step* - use before redoing every source from scratch."""
        self.run_step(step, Stage.CLEAR_OUTPUT_DIR)

    def preview_plan(
        self,
        rel_graph_stage: Stage = Stage.EXTRACT_AND_POPULATE,
        enrichment_stage: Stage = Stage.EXTRACT_AND_POPULATE,
    ) -> None:
        """
        Print the full (book, step, stage, method) plan WITHOUT running anything - no DB or
        LLM calls. Sanity-check a large run (e.g. all of Tanach + Bavli) before committing.
        """
        print(f"\n{'='*70}")
        print(f"PLAN: {'examples only' if self.use_examples else str(len(self.books)) + ' book(s)'}, "
              f"model={self.model_provider.value}, max_sources_per_book={self.max_sources_per_book}, "
              f"json_only={self.json_only}")
        print(f"{'='*70}")
        for book in self._targets():
            for step, stage in ((Step.ENTITY_REL_GRAPH, rel_graph_stage),
                                 (Step.ENTITY_ENRICHMENT, enrichment_stage)):
                stage = self._effective_stage(step, stage)
                method_name = _STAGE_METHOD[(step, stage)]
                print(f"  {self._book_label(book):<28} "
                      f"{step.value:<18} {stage.value:<20} -> {method_name}()")
        print(f"{'='*70}\n")

    def find_unprocessed_sources(self, books: Optional[Sequence[Book]] = None) -> Dict[Book, Dict[str, List[str]]]:
        """
        Read-only DB check (no LLM calls, no writes). For each book (default: self.books),
        prints and returns the source keys where a step did not (fully) run:
          "rel_graph_missing" - no SourceMetadata exists for the source content, i.e. the
              rel-graph population never ran for it.
          "enrichment_missing" - SourceMetadata exists, but some of its linked entities
              still have no metadata (enrichment didn't run / didn't finish).
        Returns {book: {"rel_graph_missing": [...], "enrichment_missing": [...]}}.
        """
        books = list(books) if books is not None else list(self.books)
        cls = DBPopulateEntityEnrichment
        if cls not in self._initialized_classes:
            cls.setUpClass()
            self._initialized_classes.append(cls)
        db_api = cls.db_api

        report: Dict[Book, Dict[str, List[str]]] = {}
        for book in books:
            rel_missing: List[str] = []
            enrich_missing: List[str] = []
            for src_content in db_api.get_all_src_contents_by_book(book):
                src_metadata = db_api.get_source_metadata_by_key(src_content.key)
                if src_metadata is None:
                    rel_missing.append(src_content.key)
                    continue
                if not src_metadata.entity_keys:
                    continue
                entities = db_api.get_entities_by_keys(list(src_metadata.entity_keys))
                if any(not e.has_metadata() for e in entities):
                    enrich_missing.append(src_content.key)
            report[book] = {"rel_graph_missing": rel_missing, "enrichment_missing": enrich_missing}

        print(f"\n{'='*70}\nUNPROCESSED SOURCES REPORT\n{'='*70}")
        all_rel: List[str] = []
        all_enrich: List[str] = []
        for book, res in report.items():
            print(f"{self._book_label(book)}: "
                  f"{len(res['rel_graph_missing'])} without rel-graph metadata, "
                  f"{len(res['enrichment_missing'])} with un-enriched entities")
            all_rel += res["rel_graph_missing"]
            all_enrich += res["enrichment_missing"]
        # Copy-paste-ready Python lists, e.g. EntityPipelineRunner(source_keys=REL_GRAPH_MISSING)
        print("\n# Paste into EntityPipelineRunner(source_keys=...) and run run_full_pipeline():")
        print(f"REL_GRAPH_MISSING = {self._format_list(all_rel)}")
        print("\n# Rel-graph already ran - paste and run_step(Step.ENTITY_ENRICHMENT):")
        print(f"ENRICHMENT_MISSING = {self._format_list(all_enrich)}")
        print(f"{'='*70}\n")
        return report

    @staticmethod
    def _format_list(keys: List[str]) -> str:
        if not keys:
            return "[]"
        return "[\n" + "".join(f"    {key!r},\n" for key in keys) + "]"

    def close(self) -> None:
        """Disconnect the shared DB connection. Call once, after ALL runs are done."""
        for cls in self._initialized_classes:
            if cls.db_api is not None:
                cls.db_api.disconnect()
                break  # db_api is the same underlying singleton connection for every class

    # ─── Internals ─────────────────────────────────────────────────────────

    def _run_one(self, step: Step, book: Optional[Book], stage: Stage, continue_on_error: bool) -> None:
        cls = _STEP_CLASS[step]
        stage = self._effective_stage(step, stage)
        method_name = _STAGE_METHOD[(step, stage)]
        self._print_banner(step, book, stage, method_name)

        if cls not in self._initialized_classes:
            cls.setUpClass()
            self._initialized_classes.append(cls)

        instance = cls(method_name)
        setattr(instance, _STEP_BOOK_ATTR[step], book)
        instance.model_provider = self.model_provider
        instance.max_sources_to_extract = self.max_sources_per_book
        instance.use_examples = self.use_examples
        instance.source_keys_filter = self.source_keys_by_book.get(book)
        instance.skip_db_writes = self.json_only
        instance.setUp()

        try:
            if self.use_examples and stage in (Stage.EXTRACT_AND_POPULATE, Stage.EXTRACT_ONLY):
                instance.test_force_clear_output_dir()
            getattr(instance, method_name)()
            self.results.append(_BookRunResult(step, book, stage, ok=True))
        except Exception as e:
            self.results.append(_BookRunResult(step, book, stage, ok=False, error=str(e)))
            print(f"\n{'!'*70}\nFAILED: {step.value} / {self._book_label(book)} / {stage.value}: {e}\n{'!'*70}")
            if not continue_on_error:
                raise
        finally:
            # Mirrors each populator's own tearDown() EXCEPT the DB disconnect: closing the
            # Gemini context-cache resource is cheap/safe per-instance cleanup, but
            # disconnecting the shared DB singleton here would break every subsequent
            # (book, step) in this run - see DBapiMongoDB's @singleton: once disconnected,
            # nothing in this process can reconnect it except by constructing a brand new
            # instance, which the singleton decorator specifically prevents. The DB is
            # disconnected once, at the very end of the whole run, by close().
            getattr(instance, _STEP_CALLER_ATTR[step]).close()

    @staticmethod
    def _book_label(book: Optional[Book]) -> str:
        return "EXAMPLES" if book is None else f"[{book.source_type.value}] {book.database_name}"

    def _print_banner(self, step: Step, book: Optional[Book], stage: Stage, method_name: str) -> None:
        print(f"\n{'#'*70}")
        print(f"# STEP={step.value}  BOOK={self._book_label(book)}  STAGE={stage.value}  -> {method_name}()")
        print(f"{'#'*70}\n")

    def _print_summary(self) -> None:
        failed = [r for r in self.results if not r.ok]
        print(f"\n{'='*70}")
        print(f"RUN SUMMARY: {len(self.results)} (book, step) run(s), {len(failed)} failed.")
        for r in failed:
            print(f"  FAILED: {r.step.value} / {self._book_label(r.book)} / {r.stage.value}: {r.error}")
        print(f"{'='*70}\n")


class EntityPipelineRunnerTests(unittest.TestCase):
    """PyCharm-runnable entry points (click the gutter Run icon on a method)."""

    def test_find_unprocessed_sources(self) -> None:
        """Edit BOOKS_TO_CHECK, run, then copy the printed lists."""
        BOOKS_TO_CHECK = [Books.GENESIS, Books.EXODUS]
        runner = EntityPipelineRunner(books=BOOKS_TO_CHECK)
        try:
            runner.find_unprocessed_sources()
        finally:
            runner.close()

    def test_run_specific_sources(self) -> None:
        """Paste source keys (from the report) below, then run."""
        SOURCE_KEYS = [
            # 'TN_Genesis_0_6:14-25',
        ]
        runner = EntityPipelineRunner(source_keys=SOURCE_KEYS, model_provider=ModelProvider.GEMINI_PAID)
        try:
            runner.preview_plan()
            runner.run_full_pipeline()
        finally:
            runner.close()

    def test_run_enrichment_missing_sources(self) -> None:
        """Paste ENRICHMENT_MISSING keys here to run entity enrichment only."""
        ENRICHMENT_MISSING = [

                'TN_Genesis_0_1:6-9',
                'TN_Genesis_0_1:12-13',
                'TN_Genesis_0_1:14-19',
                'TN_Genesis_0_1:20-23',
                'TN_Genesis_0_1:26-27',
                'TN_Genesis_0_1:28-2:1',
                'TN_Genesis_0_2:2-7',
                'TN_Genesis_0_3:2-5',
                'TN_Genesis_0_3:9-11',
                'TN_Genesis_0_3:12-13',
                'TN_Genesis_0_3:14-19',
                'TN_Genesis_0_3:20',
                'TN_Genesis_0_3:21-24',
                'TN_Genesis_0_4:1-2',
                'TN_Genesis_0_4:3-7',
                'TN_Genesis_0_4:8-12',
                'TN_Genesis_0_4:13-16',
                'TN_Genesis_0_4:17-18',
                'TN_Genesis_0_4:19-22',
                'TN_Genesis_0_4:23-24',
                'TN_Genesis_0_4:25-5:21',
                'TN_Genesis_0_5:22-32',
                'TN_Genesis_0_6:4-5',
                'TN_Genesis_0_6:6-8',
                'TN_Genesis_0_6:9-13',
                'TN_Genesis_0_6:14-18',
                'TN_Genesis_0_6:19-7:4',
                'TN_Genesis_0_7:5-11',
                'TN_Genesis_0_7:12-8:3',
                'TN_Genesis_0_8:4-6',
                'TN_Genesis_0_8:7-12',
                'TN_Genesis_0_8:13-15',
                'TN_Genesis_0_8:16-9:4',
                'TN_Genesis_0_9:5-12',
                'TN_Genesis_0_9:13-24',
                'TN_Genesis_0_9:25-27',
                'TN_Genesis_0_9:28-10:8',
                'TN_Genesis_0_10:9-20',
                'TN_Genesis_0_10:21-11:3',
                'TN_Genesis_0_11:4-6',
                'TN_Genesis_0_11:10-25',
                'TN_Genesis_0_11:26-32',
                'TN_Genesis_0_12:1-3',
                'TN_Genesis_0_12:4-6',
                'TN_Genesis_0_12:7-9',
                'TN_Genesis_0_12:10-16',
                'TN_Genesis_0_12:17-13:4',
                'TN_Genesis_0_13:5-10',
                'TN_Genesis_0_13:11-13',
                'TN_Genesis_0_13:14-14:1',
                'TN_Genesis_0_14:2-11',
                'TN_Genesis_0_14:12-24',
                'TN_Genesis_0_15:1-8',
                'TN_Genesis_0_15:9-21',
                'TN_Genesis_0_16:1-5',
                'TN_Genesis_0_16:6-10',
                'TN_Genesis_0_16:11-16',
                'TN_Genesis_0_17:1-3',
                'TN_Genesis_0_17:4-14',
                'TN_Genesis_0_17:15-17',
                'TN_Genesis_0_17:18-22',
                'TN_Genesis_0_18:1-4',
                'TN_Genesis_0_18:5-9',
                'TN_Genesis_0_18:10-15',
                'TN_Genesis_0_18:16-22',
                'TN_Genesis_0_18:23',
                'TN_Genesis_0_18:24-27',
                'TN_Genesis_0_18:28-33',
                'TN_Genesis_0_19:1-3',
                'TN_Genesis_0_19:4-9',
                'TN_Genesis_0_19:10-18',
                'TN_Genesis_0_19:19-23',
                'TN_Genesis_0_19:24-29',
                'TN_Genesis_0_19:30-38',
                'TN_Genesis_0_20:1-2',
                'TN_Genesis_0_20:3-8',
                'TN_Genesis_0_20:9-13',
                'TN_Genesis_0_20:14-18',
                'TN_Genesis_0_21:1-8',
                'TN_Genesis_0_21:9-16',
                'TN_Genesis_0_21:17-21',
                'TN_Genesis_0_21:22-26',
                'TN_Genesis_0_21:27-34',
                'TN_Genesis_0_22:1-6',
                'TN_Genesis_0_22:7-10',
                'TN_Genesis_0_22:11-15',
                'TN_Genesis_0_22:16-19',
                'TN_Genesis_0_22:20-24',
                'TN_Genesis_0_23:1-8',
                'TN_Genesis_0_23:9',
                'TN_Genesis_0_23:10-20',
                'TN_Genesis_0_24:1-3',
                'TN_Genesis_0_24:4-11',
                'TN_Genesis_0_24:12-15',
                'TN_Genesis_0_24:18-32',
                'TN_Genesis_0_24:33-49',
                'TN_Genesis_0_24:50-61',
                'TN_Genesis_0_24:62-67',
                'TN_Genesis_0_25:1',
                'TN_Genesis_0_25:2-6',
                'TN_Genesis_0_25:7-10',
                'TN_Genesis_0_25:11-18',
                'TN_Genesis_0_25:19-22',
                'TN_Genesis_0_25:23-26',
                'TN_Genesis_0_25:27-32',
                'TN_Genesis_0_25:33-34',
                'TN_Genesis_0_26:1-10',
                'TN_Genesis_0_26:11-17',
                'TN_Genesis_0_26:18-22',
                'TN_Genesis_0_26:23-33',
                'TN_Genesis_0_26:34-35',
                'TN_Genesis_0_27:1-5',
                'TN_Genesis_0_27:6-17',
                'TN_Genesis_0_27:18-20',
                'TN_Genesis_0_27:21-29',
                'TN_Genesis_0_27:30-38',
                'TN_Genesis_0_27:39-41',
                'TN_Genesis_0_27:42-28:5',
                'TN_Genesis_0_28:6-10',
                'TN_Genesis_0_28:11-19',
                'TN_Genesis_0_29:2-8',
                'TN_Genesis_0_29:9-17',
                'TN_Genesis_0_29:18-22',
                'TN_Genesis_0_29:23-31',
                'TN_Genesis_0_29:32-30:2',
                'TN_Genesis_0_30:3-8',
                'TN_Genesis_0_30:9-16',
                'TN_Genesis_0_30:17-22',
                'TN_Genesis_0_30:23-24',
                'TN_Genesis_0_30:25-36',
                'TN_Genesis_0_30:37-42',
                'TN_Genesis_0_30:43-31:2',
                'TN_Genesis_0_31:3-13',
                'TN_Genesis_0_31:14-22',
                'TN_Genesis_0_31:23-25',
                'TN_Genesis_0_31:26-30',
                'TN_Genesis_0_31:31-35',
                'TN_Genesis_0_31:36-43',
                'TN_Genesis_0_31:44-32:3',
                'TN_Genesis_0_32:4-6',
                'TN_Genesis_0_32:7-9',
                'TN_Genesis_0_32:10-14',
                'TN_Genesis_0_32:15-24',
                'TN_Genesis_0_32:25-33',
                'TN_Genesis_0_33:1-10',
                'TN_Genesis_0_33:11-15',
                'TN_Genesis_0_33:16-17',
                'TN_Genesis_0_33:18-34:1',
                'TN_Genesis_0_34:2-12',
                'TN_Genesis_0_34:13-24',
                'TN_Genesis_0_34:25-29',
                'TN_Genesis_0_34:30-31',
                'TN_Genesis_0_35:1-9',
                'TN_Genesis_0_35:10-15',
                'TN_Genesis_0_35:16-26',
                'TN_Genesis_0_35:27-29',
                'TN_Genesis_0_36:1-19',
                'TN_Genesis_0_36:20-30',
                'TN_Genesis_0_36:31-43',
                'TN_Genesis_0_37:1-4',
                'TN_Genesis_0_37:9-12',
                'TN_Genesis_0_37:13-19',
                'TN_Genesis_0_37:25-30',
                'TN_Genesis_0_37:31-36',
                'TN_Genesis_0_38:1-6',
                'TN_Genesis_0_38:7-12',
                'TN_Genesis_0_38:13-23',
                'TN_Genesis_0_38:24-26',
                'TN_Genesis_0_38:27-30',
                'TN_Genesis_0_39:1-7',
                'TN_Genesis_0_39:14-23',
                'TN_Genesis_0_40:1-8',
                'TN_Genesis_0_40:9-15',
                'TN_Genesis_0_41:1-8',
                'TN_Genesis_0_41:25-39',
                'TN_Genesis_0_41:40-46',
                'TN_Genesis_0_41:47-53',
                'TN_Genesis_0_41:54-57',
                'TN_Genesis_0_42:9-20',
                'TN_Genesis_0_42:29-38',
                'TN_Genesis_0_43:14-18',
                'TN_Genesis_0_43:26-34',
                'TN_Genesis_0_44:1-9',
                'TN_Genesis_0_44:10-16',
                'TN_Genesis_0_44:18-34',
                'TN_Genesis_0_45:1-9',
                'TN_Genesis_0_45:10-15',
                'TN_Genesis_0_46:1-7',
                'TN_Genesis_0_46:8-28',
                'TN_Genesis_0_46:29-34',
                'TN_Genesis_0_47:13-19',
                'TN_Genesis_0_48:1-5',
                'TN_Genesis_0_48:6-13',
                'TN_Genesis_0_48:14-21',
                'TN_Genesis_0_49:8-9',
                'TN_Genesis_0_49:10-12',
                'TN_Genesis_0_49:22-26',
                'TN_Genesis_0_49:27-28',
                'TN_Genesis_0_49:29-50:3',
                'TN_Genesis_0_50:7-14',
                'TN_Genesis_0_50:15-23',
                'TN_Genesis_0_50:24-26',
                'TN_Exodus_0_1:1-7',
                'TN_Exodus_0_1:15-22',
                'TN_Exodus_0_2:1-4',
                'TN_Exodus_0_2:7-11',
                'TN_Exodus_0_2:12-15',
                'TN_Exodus_0_2:16-22',
                'TN_Exodus_0_2:23-3:1',
                'TN_Exodus_0_3:6-10',
                'TN_Exodus_0_3:13-15',
                'TN_Exodus_0_3:16-22',
                'TN_Exodus_0_4:5-9',
                'TN_Exodus_0_4:10-17',
                'TN_Exodus_0_4:18-23',
                'TN_Exodus_0_4:24-26',
                'TN_Exodus_0_4:27-31',
                'TN_Exodus_0_5:1-5',
                'TN_Exodus_0_5:14-21',
                'TN_Exodus_0_6:1-4',
                'TN_Exodus_0_6:5-13',
                'TN_Exodus_0_6:14-25',
                'TN_Exodus_0_6:26-30',
                'TN_Exodus_0_7:1-9',
                'TN_Exodus_0_7:10-13',
                'TN_Exodus_0_7:14-19',
                'TN_Exodus_0_7:20-25',
                'TN_Exodus_0_7:26-8:1',
                'TN_Exodus_0_8:2-11',
                'TN_Exodus_0_8:12-15',
                'TN_Exodus_0_8:16-28',
                'TN_Exodus_0_9:8-12',
                'TN_Exodus_0_9:13-35',
                'TN_Exodus_0_10:1-6',
                'TN_Exodus_0_10:7-20',
                'TN_Exodus_0_10:21-29',
                'TN_Exodus_0_11:1-10',
                'TN_Exodus_0_12:1-2',
                'TN_Exodus_0_12:12-13',
                'TN_Exodus_0_12:14-16',
                'TN_Exodus_0_12:17-20',
                'TN_Exodus_0_12:21-25',
                'TN_Exodus_0_12:26-28',
                'TN_Exodus_0_12:29-34',
                'TN_Exodus_0_12:43-47',
                'TN_Exodus_0_12:48-51',
                'TN_Exodus_0_13:3-7',
                'TN_Exodus_0_14:1-4',
                'TN_Exodus_0_14:9-14',
                'TN_Exodus_0_15:14-16',
                'TN_Exodus_0_15:20-21',
                'TN_Exodus_0_15:22-16:1',
                'TN_Exodus_0_16:2-3',
                'TN_Exodus_0_16:4-12',
                'TN_Exodus_0_16:13-21',
                'TN_Exodus_0_16:27-31',
                'TN_Exodus_0_16:32-36',
                'TN_Exodus_0_17:8-13',
                'TN_Exodus_0_18:1-6',
                'TN_Exodus_0_18:7-11',
                'TN_Exodus_0_18:12',
                'TN_Exodus_0_18:13-18',
                'TN_Exodus_0_18:19-23',
                'TN_Exodus_0_18:24-27',
                'TN_Exodus_0_19:3-4',
                'TN_Exodus_0_19:5-7',
                'TN_Exodus_0_19:8-9',
                'TN_Exodus_0_19:10-15',
                'TN_Exodus_0_19:16-17',
                'TN_Exodus_0_19:21-20:1',
                'TN_Exodus_0_20:3-6',
                'TN_Exodus_0_20:8-11',
                'TN_Exodus_0_20:12-14',
                'TN_Exodus_0_21:1-2',
                'TN_Exodus_0_21:20-21',
                'TN_Exodus_0_22:28-29',
                'TN_Exodus_0_23:10-12',
                'TN_Exodus_0_23:13-18',
                'TN_Exodus_0_23:19',
                'TN_Exodus_0_23:20-33',
                'TN_Exodus_0_24:1-5',
                'TN_Exodus_0_24:6-11',
                'TN_Exodus_0_24:12-18',
                'TN_Exodus_0_25:1-9',
                'TN_Exodus_0_26:1-14',
                'TN_Exodus_0_26:15-30',
                'TN_Exodus_0_26:36-37',
                'TN_Exodus_0_27:1-8',
                'TN_Exodus_0_27:9-19',
                'TN_Exodus_0_27:20-21',
                'TN_Exodus_0_28:1-5',
                'TN_Exodus_0_28:6-14',
                'TN_Exodus_0_28:15-30',
                'TN_Exodus_0_28:31-35',
                'TN_Exodus_0_28:36-38',
                'TN_Exodus_0_28:39-43',
                'TN_Exodus_0_29:1-14',
                'TN_Exodus_0_29:15-18',
                'TN_Exodus_0_29:19-25',
                'TN_Exodus_0_29:26-30',
                'TN_Exodus_0_29:31-35',
                'TN_Exodus_0_29:36-37',
                'TN_Exodus_0_29:38-46',
                'TN_Exodus_0_30:1-10',
                'TN_Exodus_0_30:17-21',
                'TN_Exodus_0_30:22-33',
                'TN_Exodus_0_31:2-11',
                'TN_Exodus_0_31:12-18',
                'TN_Exodus_0_32:1-6',
                'TN_Exodus_0_32:11-14',
                'TN_Exodus_0_32:20-25',
                'TN_Exodus_0_32:26-29',
                'TN_Exodus_0_32:34-33:3',
                'TN_Exodus_0_33:4-6',
                'TN_Exodus_0_34:1-3',
                'TN_Exodus_0_34:4-10',
                'TN_Exodus_0_34:11-17',
                'TN_Exodus_0_34:18',
                'TN_Exodus_0_34:21-27',
                'TN_Exodus_0_34:28',
                'TN_Exodus_0_34:29-35',
                'TN_Exodus_0_35:1-3',
                'TN_Exodus_0_35:4-20',
                'TN_Exodus_0_35:21-29',
                'TN_Exodus_0_35:30-36:7',
                'TN_Exodus_0_36:8-19',
                'TN_Exodus_0_36:20-34',
                'TN_Exodus_0_37:1-5',
                'TN_Exodus_0_37:6-9',
                'TN_Exodus_0_37:25-29',
                'TN_Exodus_0_38:1-7',
                'TN_Exodus_0_38:9-20',
                'TN_Exodus_0_38:21-31',
                'TN_Exodus_0_39:1-7',
                'TN_Exodus_0_39:8-21',
                'TN_Exodus_0_39:27-32',
                'TN_Exodus_0_39:33-43',
                'TN_Exodus_0_40:12-16',
                'TN_Exodus_0_40:17-33',

        ]
        if not ENRICHMENT_MISSING:
            raise ValueError("Paste source keys into ENRICHMENT_MISSING before running.")

        runner = EntityPipelineRunner(
            source_keys=ENRICHMENT_MISSING,
            model_provider=ModelProvider.GEMINI_PAID,
        )
        try:
            runner.run_step(Step.ENTITY_ENRICHMENT)
        finally:
            runner.close()

if __name__ == "__main__":
    # ====== EDIT THIS CONFIG, THEN RUN THIS FILE DIRECTLY ======
    books = [
        Books.GENESIS,
        Books.EXODUS,
        Books.LEVITICUS,
        Books.NUMBERS,
        Books.DEUTERONOMY,
        Books.JOSHUA,
        Books.JUDGES,
        Books.SAMUEL_I,
        Books.SAMUEL_II,
        Books.KINGS_I,
        Books.KINGS_II,
        Books.ISAIAH,
        Books.JEREMIAH,
        Books.EZEKIEL,
        Books.HOSEA,
        Books.JOEL,
        Books.AMOS,
        Books.OBADIAH,
        Books.JONAH,
        Books.MICAH,
        Books.NAHUM,
        Books.HABAKKUK,
        Books.ZEPHANIAH,
        Books.HAGGAI,
        Books.ZECHARIAH,
        Books.MALACHI,
        Books.PSALMS,
        Books.PROVERBS,
        Books.JOB,
        Books.SONG_OF_SONGS,
        Books.RUTH,
        Books.LAMENTATIONS,
        Books.ECCLESIASTES,
        Books.ESTHER,
        Books.DANIEL,
        Books.EZRA,
        Books.NEHEMIAH,
        Books.CHRONICLES_I,
        Books.CHRONICLES_II,
    ]
    runner = EntityPipelineRunner(
        books=books,                    # uncomment the books to process
        model_provider=ModelProvider.GEMINI_PAID,
        # model_provider=ModelProvider.GEMINI_LEGACY_PAID,  # Uses GEMINI_LEGACY_PAID_API_KEY
        max_sources_per_book=None,      # None = whole book; set an int for a cheap smoke test first
        use_examples=False,             # True = ignore books; run only get_examples_src_contents passages
        # use_examples=True,             # True = ignore books; run only get_examples_src_contents passages
        json_only=False,                # True = LLM calls -> JSON/TXT files only, no DB writes
        # json_only=True,                # True = LLM calls -> JSON/TXT files only, no DB writes
    )
    try:
        runner.run_step(Step.ENTITY_REL_GRAPH)
        runner.run_step(Step.ENTITY_ENRICHMENT)
    finally:
        runner.close()
    # =============================================================
