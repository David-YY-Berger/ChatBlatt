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
        books: Sequence[Book],
        model_provider: ModelProvider = ModelProvider.GEMINI_PAID,
        max_sources_per_book: Optional[int] = None,
    ):
        """
        books: the books to process, IN ORDER (e.g. TANACH_BOOKS, BAVLI_BOOKS, ALL_BOOKS,
            or a hand-picked list like [Books.GENESIS, Books.BERAKHOT]).
        model_provider: LLM provider/model used for every call this run makes.
        max_sources_per_book: caps each book to its first N sources (book order) - None
            (default) processes the whole book. Set an int for a cheap/quick smoke test
            across many books before committing to a full run.
        """
        self.books = list(books)
        self.model_provider = model_provider
        self.max_sources_per_book = max_sources_per_book
        self._initialized_classes: List[Type[DBPopulateLlmBase]] = []
        self.results: List[_BookRunResult] = []

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
        for book in self.books:
            self._run_one(Step.ENTITY_REL_GRAPH, book, rel_graph_stage, continue_on_error)
            self._run_one(Step.ENTITY_ENRICHMENT, book, enrichment_stage, continue_on_error)
        self._print_summary()

    def run_step(self, step: Step, stage: Stage = Stage.EXTRACT_AND_POPULATE,
                 continue_on_error: bool = False) -> None:
        """Run a single step (just rel-graph, or just enrichment) for every book, in order."""
        for book in self.books:
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
        print(f"PLAN: {len(self.books)} book(s), model={self.model_provider.value}, "
              f"max_sources_per_book={self.max_sources_per_book}")
        print(f"{'='*70}")
        for book in self.books:
            for step, stage in ((Step.ENTITY_REL_GRAPH, rel_graph_stage),
                                 (Step.ENTITY_ENRICHMENT, enrichment_stage)):
                method_name = _STAGE_METHOD[(step, stage)]
                print(f"  [{book.source_type.value}] {book.database_name:<20} "
                      f"{step.value:<18} {stage.value:<20} -> {method_name}()")
        print(f"{'='*70}\n")

    def close(self) -> None:
        """Disconnect the shared DB connection. Call once, after ALL runs are done."""
        for cls in self._initialized_classes:
            if cls.db_api is not None:
                cls.db_api.disconnect()
                break  # db_api is the same underlying singleton connection for every class

    # ─── Internals ─────────────────────────────────────────────────────────

    def _run_one(self, step: Step, book: Book, stage: Stage, continue_on_error: bool) -> None:
        cls = _STEP_CLASS[step]
        method_name = _STAGE_METHOD[(step, stage)]
        self._print_banner(step, book, stage, method_name)

        if cls not in self._initialized_classes:
            cls.setUpClass()
            self._initialized_classes.append(cls)

        instance = cls(method_name)
        setattr(instance, _STEP_BOOK_ATTR[step], book)
        instance.model_provider = self.model_provider
        instance.max_sources_to_extract = self.max_sources_per_book
        instance.setUp()

        try:
            getattr(instance, method_name)()
            self.results.append(_BookRunResult(step, book, stage, ok=True))
        except Exception as e:
            self.results.append(_BookRunResult(step, book, stage, ok=False, error=str(e)))
            print(f"\n{'!'*70}\nFAILED: {step.value} / {book.database_name} / {stage.value}: {e}\n{'!'*70}")
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
    def _print_banner(step: Step, book: Book, stage: Stage, method_name: str) -> None:
        print(f"\n{'#'*70}")
        print(f"# STEP={step.value}  BOOK={book.database_name}  STAGE={stage.value}  -> {method_name}()")
        print(f"{'#'*70}\n")

    def _print_summary(self) -> None:
        failed = [r for r in self.results if not r.ok]
        print(f"\n{'='*70}")
        print(f"RUN SUMMARY: {len(self.results)} (book, step) run(s), {len(failed)} failed.")
        for r in failed:
            print(f"  FAILED: {r.step.value} / {r.book.database_name} / {r.stage.value}: {r.error}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    # ====== EDIT THIS CONFIG, THEN RUN THIS FILE DIRECTLY ======
    runner = EntityPipelineRunner(
        books=[Books.BERAKHOT],         # e.g. TANACH_BOOKS, BAVLI_BOOKS, ALL_BOOKS, or a hand-picked list
        model_provider=ModelProvider.GEMINI_PAID,
        max_sources_per_book=None,      # None = whole book; set an int for a cheap smoke test first
    )
    try:
        # runner.run_step(Step.ENTITY_REL_GRAPH)
        runner.run_step(Step.ENTITY_ENRICHMENT)
    finally:
        runner.close()
    # =============================================================
