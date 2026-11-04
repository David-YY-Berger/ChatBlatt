# bs"d
"""
RerunMissingSourcesRunner - re-runs the entity pipeline ONLY for sources that were never run.

Use after an EntityPipelineRunner run where some sources failed (e.g. enrichment/LLM calls with
retries=0) and were never retried.

A source counts as "not yet run" when it has NO SourceMetadata document in the DB. Before any
such source is re-sent to the LLM, it is also checked against the real_data output dirs
(Paths.ENTITY_REL_GRAPH_REAL_DATA_DIR): if ANY file (.json or .txt) for that source key already
exists anywhere under that tree, the source is NOT re-run (its LLM output already exists - it's
just not in the DB yet). Those are reported separately; set populate_existing_files=True to
write them to the DB from the existing JSONs (no LLM call).

Existing runners/populators are reused as-is (EntityPipelineRunner + source_keys_filter); no
population logic lives here. See control_docs/pipeline/entity_pipeline_runner.md.

    runner = RerunMissingSourcesRunner(books=ALL_BOOKS)
    try:
        runner.preview_missing()      # read-only: DB + file checks, no LLM, no writes
        runner.run_missing()          # rel-graph then enrichment for just the missing sources
    finally:
        runner.close()

Like EntityPipelineRunner, this writes to the real DB (no test DB).
"""

import os
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set

from backend.common import Paths
from backend.db.Collections import CollectionObjs
from backend.db.data_names.Books import Book
from backend.db.DBConstants import DBFields
from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelProvider
from backend_pipeline.data_pipeline.populator_scripts.DBPopulateEntityRelGraph import DBPopulateEntityRelGraph
from backend_pipeline.data_pipeline.populator_scripts.EntityPipelineRunner import (
    ALL_BOOKS, EntityPipelineRunner, Stage, Step,
)


def _norm(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


@dataclass
class _BookMissing:
    book: Book
    to_rerun: List[str] = field(default_factory=list)       # no metadata, no file -> LLM rerun
    file_exists: List[str] = field(default_factory=list)    # no metadata, but a file exists -> skip


class RerunMissingSourcesRunner(EntityPipelineRunner):
    def __init__(
        self,
        books: Sequence[Book] = ALL_BOOKS,
        model_provider: ModelProvider = ModelProvider.GEMINI_PAID,
        populate_existing_files: bool = False,
    ):
        super().__init__(books=books, model_provider=model_provider, max_sources_per_book=None)
        self.populate_existing_files = populate_existing_files
        self.source_keys_filter: Optional[List[str]] = None
        self._file_stems: Optional[Set[str]] = None

    # ─── Detection (read-only) ─────────────────────────────────────────────

    def _ensure_db(self) -> None:
        cls = DBPopulateEntityRelGraph
        if cls not in self._initialized_classes:
            cls.setUpClass()
            self._initialized_classes.append(cls)

    def _existing_file_stems(self) -> Set[str]:
        """Normalized filename stems of every file anywhere under the rel-graph real_data tree."""
        if self._file_stems is None:
            stems: Set[str] = set()
            for root, _dirs, files in os.walk(Paths.ENTITY_REL_GRAPH_REAL_DATA_DIR):
                for f in files:
                    stem, ext = os.path.splitext(f)
                    if ext.lower() in (".json", ".txt"):
                        stems.add(_norm(stem))
            self._file_stems = stems
        return self._file_stems

    @staticmethod
    def _key_to_stem(key: str) -> str:
        return _norm(key.replace(":", ";"))

    def find_missing_sources(self) -> Dict[str, _BookMissing]:
        self._ensure_db()
        db = DBPopulateEntityRelGraph.db_api
        with_metadata = {
            d[DBFields.KEY]
            for d in db.get_collection(CollectionObjs.SRC_METADATA).find({}, {DBFields.KEY: 1, "_id": 0})
        }
        stems = self._existing_file_stems()
        result: Dict[str, _BookMissing] = {}
        for book in self.books:
            missing = _BookMissing(book)
            for content in db.get_all_src_contents_by_book(book):
                if content.key in with_metadata:
                    continue
                if self._key_to_stem(content.key) in stems:
                    missing.file_exists.append(content.key)
                else:
                    missing.to_rerun.append(content.key)
            result[book.database_name] = missing
        return result

    def preview_missing(self) -> Dict[str, _BookMissing]:
        res = self.find_missing_sources()
        print(f"\n{'='*70}\nMISSING SOURCES (no SourceMetadata in DB)\n{'='*70}")
        total_rerun = total_file = 0
        for name, m in res.items():
            if m.to_rerun or m.file_exists:
                print(f"  {name:<28} rerun(LLM)={len(m.to_rerun):<5} file-exists-skip={len(m.file_exists)}")
            total_rerun += len(m.to_rerun)
            total_file += len(m.file_exists)
        print(f"TOTAL: {total_rerun} to re-run via LLM, {total_file} skipped because a file already exists")
        print(f"{'='*70}\n")
        return res

    # ─── Run ───────────────────────────────────────────────────────────────

    def run_missing(self, continue_on_error: bool = True) -> None:
        res = self.preview_missing()
        for m in res.values():
            if m.to_rerun:
                self.source_keys_filter = m.to_rerun
                self._run_one(Step.ENTITY_REL_GRAPH, m.book, Stage.EXTRACT_AND_POPULATE, continue_on_error)
                self._run_one(Step.ENTITY_ENRICHMENT, m.book, Stage.EXTRACT_AND_POPULATE, continue_on_error)
            if self.populate_existing_files and m.file_exists:
                # Phase 2 only, no LLM; reads the book's existing JSONs (idempotent), then enriches them.
                self.source_keys_filter = m.file_exists
                self._run_one(Step.ENTITY_REL_GRAPH, m.book, Stage.POPULATE_ONLY, continue_on_error)
                self._run_one(Step.ENTITY_ENRICHMENT, m.book, Stage.EXTRACT_AND_POPULATE, continue_on_error)
        self.source_keys_filter = None
        self._print_summary()


if __name__ == "__main__":
    # ====== EDIT THIS CONFIG, THEN RUN THIS FILE DIRECTLY ======
    runner = RerunMissingSourcesRunner(
        books=ALL_BOOKS,
        model_provider=ModelProvider.GEMINI_PAID,
        populate_existing_files=False,
    )
    try:
        runner.preview_missing()    # comment out + uncomment next line to actually run
        # runner.run_missing()
    finally:
        runner.close()
    # =============================================================
