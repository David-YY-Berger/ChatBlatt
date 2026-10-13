# EntityPipelineRunner

Source of truth: `backend_pipeline/data_pipeline/populator_scripts/EntityPipelineRunner.py`.

## What this is

A thin driver that runs `DBPopulateEntityRelGraph` and/or `DBPopulateEntityEnrichment`
across any list of books — one book, all of Tanach, all of Bavli, everything — from one
place, instead of hand-editing each populator's `setUp()` and clicking "Run" book-by-book.

It is **not** a rewrite of either populator. For every `(book, step, stage)` it drives, it
builds a real instance of the existing class and calls one of its existing, already-tested
public `test_*` methods — the exact same method you'd click "Run" on in an IDE. See
`_STAGE_METHOD` in the module for the full `(Step, Stage) -> method name` table. No
population/resolution/disambiguation logic lives in this file.

## `Step` / `Stage`

- **`Step`** — which populator: `ENTITY_REL_GRAPH` or `ENTITY_ENRICHMENT`.
- **`Stage`** — which part of that populator's two-phase scaffold to run for one book:
  `EXTRACT_AND_POPULATE` (both phases, the default), `EXTRACT_ONLY` (phase 1 alone),
  `POPULATE_ONLY` (phase 2 alone, no LLM calls), `CLEAR_OUTPUT_DIR` (wipe that book's output
  dir, no DB writes).
- **Caveat:** `Stage.EXTRACT_ONLY` is DB-write-free for `ENTITY_REL_GRAPH`, but **not** for
  `ENTITY_ENRICHMENT` — that populator's phase 1 already writes each source's enrichment to
  the DB as it goes (see `population_pipeline_overview.md`'s two-phase scaffold section and
  `DBPopulateEntityEnrichment`'s own module docstring). For enrichment, `EXTRACT_ONLY` and
  `EXTRACT_AND_POPULATE` do the same thing.

## How book/model/cap overrides reach the populators

Both populators' `setUp()` read `book_to_extract`/`book_to_enrich`, `max_sources_to_extract`,
and the LLM provider via a `getattr(self, "<attr>", <hardcoded default>)` hook (see
`population_pipeline_overview.md`). The runner constructs an instance, sets those attributes,
*then* calls `instance.setUp()` — the override wins. Running either populator directly
(nothing pre-set) is completely unaffected and keeps its old hardcoded defaults.

## Multi-book DB connection handling (why `tearDown()` is never called here)

`DBParentClass.tearDown()` (the common base both populators inherit) calls
`self.db_api.disconnect()` after every test — fine for a single IDE-run test (the process
exits right after), fatal for a loop: `DBapiMongoDB` is `@singleton`
(`backend/common/Decorators.py`) — once `disconnect()` sets `self.client = None`, nothing in
the same process can reconnect it, because the singleton decorator returns the *existing*
(now-disconnected) instance on every later `DBFactory.get_prod_db_mongo()` call rather than
re-running `__init__`/`connect()`.

So the runner **never calls `instance.tearDown()`**. Per `(book, step)` it only calls
`<caller>.close()` directly (`pydantic_caller` / `enrichment_caller` — deletes that run's
Gemini context-cache resource, the other thing `tearDown()` would have done, safe/cheap to
call every time). The shared DB connection is disconnected exactly once, by
`EntityPipelineRunner.close()`, after the entire run is done — always call it in a `finally`.

`setUpClass()` (connects the DB, loads queries) is likewise called once per populator class
actually used in a run, not once per book — cheap to repeat (idempotent), but no reason to.

## Recommended workflow for a large run (e.g. all of Tanach, all of Bavli)

1. `runner.preview_plan()` — prints the full `(book, step, stage) -> method` plan, no DB/LLM
   calls. Sanity-check book list/order and stage choice before anything runs.
2. A small `max_sources_per_book` smoke test (e.g. `5`) across the real book list, full
   `run_full_pipeline()`, to catch config problems (API keys, book list typos) cheaply.
3. For a genuinely large/expensive run, consider splitting `run_full_pipeline` into its two
   steps with `Stage.EXTRACT_ONLY` for `ENTITY_REL_GRAPH` first (`run_step`), review the
   generated JSON/TXT files, *then* `Stage.POPULATE_ONLY` to commit to the DB, then move on to
   `ENTITY_ENRICHMENT`. (Remember the `ENTITY_ENRICHMENT` `EXTRACT_ONLY` caveat above — there
   this split doesn't buy you a DB-write-free look-before-you-commit step.)
4. Full run: `runner.run_full_pipeline()` with `max_sources_per_book=None`. Always `.close()`
   in a `finally`.

Everything is resumable the same way the underlying populators already are (see
`population_pipeline_overview.md`, "Phase 1 resumability & retries"): re-invoking the same
plan after a partial failure only (re-)does what wasn't already written.

`continue_on_error=True` (on `run_full_pipeline`/`run_step`) logs a failed `(book, step)` and
keeps going instead of stopping the whole run — useful for a long unattended run across every
book; inspect `runner.results` afterwards for the failures. Default is `False` (stop
immediately on the first failure) — a `setUp()`-level failure (e.g. a bad/missing API key)
always stops the run regardless of this flag, since it would just repeat for every remaining
book.

Per `conventions/safety_and_testing.md`: there is no separate test DB. Every book processed
here writes to the real, persistent DB unless the `(step, stage)` combination is DB-write-free
(see the `EXTRACT_ONLY`/`ENTITY_ENRICHMENT` caveat above).
