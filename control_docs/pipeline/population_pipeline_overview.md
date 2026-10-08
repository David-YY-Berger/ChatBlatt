# Population Pipeline — Overview

Source of truth: `backend_pipeline/data_pipeline/populator_scripts/*.py`,
`backend_pipeline/data_pipeline/DBScriptParentClass.py`.

All populators are unittest-style classes (`DBParentClass` base) whose `test_*` methods are
the entry points (run via `python -m unittest <module>.<class>.<test_method>`, same as any
other test). `DBParentClass.setUpClass` connects via `DBFactory.get_prod_db_mongo()` — see
`conventions/safety_and_testing.md` before running any of them.

## Run order

1. **`DBPopulateSourceContent`** — fetches passages from Sefaria into `Sources.*`.
2. **`DBPrePopulateAmbiguosEntitys`** — seeds well-known, name-ambiguous people (two kings
   named Joash, etc.) as separate `EPerson`s *before* any source-derived entity exists, so
   later mentions route to the right one. Details: `entity_prepopulation.md`.
3. **`DBPopulateEntityRelGraph`** — per source: extract entities + relationships via LLM,
   resolve Person mentions through `PersonDisambiguator`, write to `Graphs.*`.
4. **`DBPopulateEntityEnrichment`** — fills entity metadata (`display_heb_name`,
   `timePeriod`/`isWoman`/`isNonJew`/`isGroup`/`roles` for `EPerson`, etc.) for entities that
   fail `has_metadata()`. For `EPerson`, `timePeriod`/`isWoman`/`isNonJew`/`isGroup` are
   fill-only (set when currently `None`, never overwritten once set) — protects curated
   pre-population values (see `entity_prepopulation.md`) from being clobbered by a single
   incidental passage mention.
5. **`DBPopulateMergeEntities`** — CSV-driven merge of duplicate entities (as needed, not
   every run).
6. **`DBPopulateFaissAndBm25`** — builds the FAISS + BM25 search indexes from source content.

Steps 3–4 share a two-phase scaffold (`DBPopulateLlmBase`); step 2 and 5 are direct
JSON/CSV-driven DB writes; step 6 reads already-populated source content.

`DBPopulateLlmBase` itself is never meant to run — its `_get_output_dir`/`_extract_from_passage`/
`_process_json_entries` are unimplemented (`@abstractmethod`, raising `NotImplementedError`),
but since `DBParentClass` is a `unittest.TestCase` (not a true `ABC`), nothing stops it from
being instantiated directly. It sets `__test__ = False` so pytest-based runners won't collect
its own `test_*` methods; each concrete subclass re-enables collection with `__test__ = True`.
If you add a new `DBPopulateLlmBase` subclass, don't forget that line or it silently won't run.

## Two-phase LLM scaffold (`DBPopulateLlmBase`)

- **Phase 1** (`_extract_from_passage`, implemented per subclass): iterate sources, call the
  LLM once per source, write one JSON file per source to `_get_output_dir()` (filename =
  source key with `:` → `;`). Resumable and failure-tolerant (see below).
- **Phase 2** (`_process_json_entries`, implemented per subclass): read those JSON files
  back and write their contents to the DB.
- `test_run_extraction_and_population` (the usual entry point) chains both phases in one
  call and does **not** clear `_get_output_dir()` first — a re-invocation resumes rather than
  redoing everything. Call `test_force_clear_output_dir` first if you deliberately want every
  source redone (e.g. after a prompt change).

### Which sources phase 1 iterates

`DBPopulateLlmBase._extract_all_to_json(book=None)` defaults to a small hardcoded
debug/example source list (`get_examples_src_contents`) when no book is given — this is
fine for ad hoc prompt debugging but **not** a real run. A subclass that always wants a
specific book overrides `_extract_all_to_json` itself and reads an explicit instance
attribute set in `setUp` under a `# ====== SWITCH BOOK HERE ======` comment (same pattern as
the model-provider switch) — see `DBPopulateEntityRelGraph.book_to_extract` and
`DBPopulateEntityEnrichment.book_to_enrich`. Don't change the shared base's default/signature
to thread a book through — `DBPopulateEntityEnrichment` has its own full override of
`_extract_all_to_json` with a different signature (no `book` param) and would break.

Both `DBPopulateEntityRelGraph` and `DBPopulateEntityEnrichment` have an optional
`self.max_sources_to_extract` (`setUp`, `# ====== OPTIONAL: LIMIT TO FIRST N SOURCES ======`),
`None` by default — set it to an int to cap the run to the first N sources of
`book_to_extract`/`book_to_enrich` (book order, e.g. the first 100 of Berakhot) for a
cheap/quick test before committing to the whole book. `DBPopulateEntityEnrichment` is also
naturally bounded without this cap — it only ever calls the LLM for sources whose
`SourceMetadata.entity_keys` has an unenriched entity (i.e. sources `DBPopulateEntityRelGraph`
already processed) — but the explicit cap keeps both populators' test runs scoped to the
exact same N sources and avoids the (cheap, but non-zero) per-source metadata lookup for
every source beyond that in the book.

### Output directories (`Paths.get_entity_rel_graph_output_dir` / `get_entity_enrichment_output_dir`)

Both populators' phase 1/2 JSON+TXT output lives under a single central root,
`Paths.REAL_DATA_DIR` (a sibling folder to the repo, `ChatBlatt_data_files/real_data`, not
under version control) — **one book, one subfolder**
(`.../entity_rels/<book>` / `.../enrichment/<book>`, lowercased `Book.database_name`), via
`Paths.get_entity_rel_graph_output_dir(book_database_name)` /
`Paths.get_entity_enrichment_output_dir(book_database_name)`. Don't reintroduce a fixed
per-script constant (e.g. a single shared dir for every book) — see why below.

**Gotcha:** phase 2 (`test_populate_from_jsons` / `test_populate_entities_and_rels_from_jsons`)
reprocesses **every** `*.json` file sitting in `_get_output_dir()`, not just the file(s) this
run produced. Per-book dirs prevent *cross-book* contamination (a leftover Genesis JSON file
no longer sits in the same folder a Berakhot run reads from), but **not** staleness *within*
the same book — if the DB is ever wiped/reset and a book is re-run, that book's output dir
still has the old run's JSON files and phase 2 will re-apply them (resolved by key, falling
back to `display_en_name` if the key no longer exists — see `DBPopulateEntityEnrichment
._process_json_entries`). Clear the relevant per-book dir (`test_force_clear_output_dir`) any
time the DB has been reset since that book was last populated.

### Phase 1 resumability & retries

- The shared loop (`DBPopulateLlmBase._extract_contents_to_json`) skips any source whose
  JSON output file already exists — no LLM call — so re-running after a partial failure only
  processes what's missing.
- A source that still fails is logged and skipped (not an aborted batch); `_extract_contents_to_json`
  returns the failed keys, which are printed once at the end of phase 1, and `test_run_extraction_and_population`
  prints them again as a final `REMINDER` block after phase 2's (longer) output so they aren't
  buried and are easy to find/retry (delete their output files, then re-run).
- Transient rate-limit/server errors (HTTP 429/500/503) are retried with exponential
  backoff **inside the LLM caller itself** (`EntityRelGraphCaller._extract`, up to 6
  attempts, ~10s–320s + jitter) — this is where `google-gla` 429s from Gemini get absorbed,
  before a source is ever counted as failed. A genuine bad/invalid model output
  (`ValidationError`) is still never retried — re-asking would just burn tokens repeating
  the same mistake.
- `DBPopulateEntityEnrichment` has its own full override of `_extract_all_to_json` (different
  source list/filtering, no file-existence skip — see its "Phase 1 override" below), but
  mirrors the shared loop's catch-and-skip: the extraction call is wrapped in try/except, a
  failed source is logged and added to `failed_keys` (returned, same `REMINDER` behavior),
  and the run continues. Unlike `EntityRelGraphCaller`, `EntityEnrichmentCaller` has **no**
  internal retry/backoff (`retries=0`, single attempt) — a transient 429 there is a plain
  failed source, not absorbed before counting.

### `DBPopulateEntityRelGraph` phase 2 specifics

- Entries sorted by `source_entry_sort_key` (book order, then section — Genesis and
  Berakhot interleave if both are "book order 1").
- **One source at a time, each in its own transaction** (`run_in_transaction`). A failure
  rolls back only that source and stops the run; earlier sources stay committed. Re-running
  is safe — nothing already written is duplicated.
- Per source: (1) insert/resolve entities (Person → `PersonDisambiguator`, see
  `person_disambiguation.md`; everything else → `try_insert_entity`) — names matching the
  ignore filter are skipped (see `entity_ignore_filter.md`), and Numbers with a disallowed
  unit/value are skipped (see `data_model/entities/number.md`); (2) insert relationships,
  resolved through that source's own name→key map; (3) upsert `SourceMetadata` — including
  `passage_types`, where `_parse_passage_types` deterministically forces any LLM-assigned
  `STORY_SAGES` down to `STORY_TANACH` for a `TN` source (see `data_model/db_and_collections.md`
  SourceMetadata section for the `STORY_TANACH`/`STORY_SAGES` rule).
- **The populator never modifies existing entity documents** — names, `book_references`,
  etc. are never touched once written.

## Idempotency & transaction conventions (apply to any new populator)

- Phase 1 (LLM extraction) resumability/retry is handled once in `DBPopulateLlmBase` (see
  above) — a new populator gets it for free by using the shared scaffold, no need to
  reimplement skip-if-exists or backoff per subclass.
- Keep each transaction small (one source / one entry / a small batch) — Atlas aborts
  transactions over 60s.
- A transaction callback **must be safe to re-run from scratch** (pymongo retries it on
  transient errors) — no side effects outside the DB inside the callback.
- Prefer DB-level dedup (`try_insert_entity`/`try_insert_rel`, or a fresh
  `get_entities_by_display_en_name` query) over an in-process cache that could go stale
  across a retry.
- When DB-level dedup isn't possible (e.g. `insert_entity` has none, by design, for Person),
  track progress externally (a small JSON file mapping a stable id → DB key, written only
  *after* the transaction that created it commits) — see `entity_prepopulation.md`.
