# Gemini Context Caching (`EntityRelGraphCaller`, `EntityEnrichmentCaller`)

Source of truth: `backend_pipeline/data_pipeline/llm_api/EntityRelGraphCaller.py`,
`backend_pipeline/data_pipeline/llm_api/EntityEnrichmentCaller.py`,
`backend_pipeline/data_pipeline/llm_api/ModelConfig.py`.

## What this is and why

Both LLM callers' system prompts are identical on every call for a given run — only the
per-passage content varies. On Gemini providers, each caller's prompt is cached once per
instance as a Gemini **explicit context cache** resource (`google_cached_content`) and reused
for every call that instance makes, instead of being resent in full every time. Cached input
tokens are billed at a steep discount (see Cost below). The two calls are intentionally kept
separate (not combined); each caller manages its own cache independently.

## Per-caller status

- **`EntityRelGraphCaller`**: active and effective. System prompt ≈3,100 tokens, well above
  Gemini's cache minimum (see below). Verified live: `cache_read_tokens=3127` out of
  `input_tokens=3155` on a real call — ~99% of input served from cache.
- **`EntityEnrichmentCaller`**: implemented identically, but **dormant in practice**. Its
  system prompt is only ≈860 tokens — below Gemini's hard **1,024-token minimum** for
  cacheable content (`caches.create` raises `400 INVALID_ARGUMENT: Cached content is too
  small`). `__init__`'s try/except catches this every run and falls back to the original
  uncached/tool-based path, so it's harmless, just a no-op (one wasted cache-creation call per
  run). Kept as-is (not reverted) in case the prompt grows past 1,024 tokens later — don't
  assume it's actually caching anything without checking `usage.details['cached_content_tokens']`
  on a real call first.

## Dependency requirement

Explicit caching (`GoogleModelSettings.google_cached_content`) needs `pydantic-ai>=1.105`,
which in turn requires `pydantic>=2.12`. This forced a real dependency bump — `pydantic`
2.11.7 → 2.14.0, `pydantic-ai` 1.55.0 → 1.107.7 (see `requirements.txt` /
`requirements_ignore_old.txt`) — across the whole codebase, not just the LLM callers. This
was a deliberate, user-approved tradeoff, not an incidental side effect; if `pydantic-ai` is
ever downgraded below 1.105 for any reason, this feature silently stops activating (see
Fallback behavior below) rather than erroring.

## Mechanism

- `google_cached_content` makes pydantic-ai strip `system_instruction`, `tools`, and
  `tool_config` from every request (the cache resource owns them — Gemini rejects requests
  that supply them alongside `cached_content`). Both callers' structured output normally goes
  through pydantic-ai's default **tool-based** mode for Gemini (a function-call), which would
  silently break once `tools` is stripped. To avoid that, caching switches each agent's
  `output_type` to `NativeOutput(...)` — Gemini's native JSON-schema response mode
  (`response_schema`/`response_mime_type`), which is a `generationConfig` field, not a tool,
  and is unaffected by the strip.
- The (large, call-invariant) system prompt is therefore **not** passed as `Agent(system_prompt=...)`
  when caching is active — it lives only in the cache resource's `system_instruction`. When
  caching is inactive (non-Gemini provider, or cache creation failed — e.g. `EntityEnrichmentCaller`
  today), the agent falls back to the original tool-based output and the original
  `system_prompt=` kwarg, unchanged from before this feature existed.

## Lifecycle

- `<Caller>(use_context_cache=True)` (default) creates the cache in `__init__` with a 1-hour
  TTL (`_CONTEXT_CACHE_TTL_SECONDS`). Each populator (`DBPopulateEntityRelGraph`,
  `DBPopulateEntityEnrichment`) builds one caller instance per run (in `setUp`) and reuses it
  for every source, so the cache is naturally shared across the whole run, not recreated
  per-source.
- **Fallback behavior**: if `use_context_cache=False`, the provider isn't Gemini, or cache
  creation raises for any reason (network, quota, content too small, API change), the caller
  logs a warning and falls back to the original always-worked uncached/tool-based path.
  Caching is therefore always a (reasoned) best-effort optimization — it never changes
  whether a run can proceed, only its cost.
- **Mid-run expiry**: in `EntityRelGraphCaller` only, if a run outlives the 1-hour TTL, a call
  fails with HTTP 404 (cache resource gone); `_extract` catches that case specifically (only
  when a cache is active), recreates the cache, and retries immediately — bounded by
  `_CONTEXT_CACHE_MAX_REFRESH_ATTEMPTS` (2), separate from the existing 429/500/503
  rate-limit retry budget (different failure mode, different fix). `EntityEnrichmentCaller`
  deliberately does **not** do this — consistent with its existing "no retries" design (see
  its module docstring), a 404 there just becomes one failed source via the normal
  failed-keys/REMINDER flow, resolved by re-running (which builds a fresh instance/cache).
- **Cleanup**: `<Caller>.close()` deletes the cache resource explicitly. Each populator's
  `tearDown()` calls it so cache storage isn't billed past the end of a run while waiting out
  its TTL. Safe to call even if no cache was ever created.

## Cost estimate

`_calculate_cost` (both callers) splits `usage.input_tokens` into cached
(`usage.details['cached_content_tokens']`) and standard portions, billing the cached portion
at `_CACHE_DISCOUNT_FACTOR` (0.1) of the standard input rate — Gemini's cached-input rate has
consistently been ~10% of standard input across the Flash/Flash-Lite tiers (checked against
the pricing page, Oct 2026). This is an estimate for logging only, not a billing-accurate
computation; revisit the factor if Google's pricing page ever shows a different ratio.

Verified live (single real call, short test passage): `EntityRelGraphCaller` got
`cache_read_tokens=3127` out of `input_tokens=3155` — i.e. ~99% of the request's input came
from the cache, with only the new passage text sent fresh. Savings scale with how much larger
the system prompt is relative to the per-call variable content — which is also exactly why
`EntityEnrichmentCaller` doesn't benefit today (small prompt, and a per-call entity-JSON list
that's proportionally larger).

## Known pre-existing noise (not fixed here)

`ModelConfig.PYDANTIC_PREFIXES` uses `"google-gla:"` for all Gemini variants, which
`pydantic-ai>=1.105` warns is deprecated in favor of `"google:"` (removal targeted for
pydantic-ai v2.0, not yet adopted here — see `requirements_ignore_old.txt` pin). Left as-is
since it's unrelated to caching and still fully functional; revisit if/when the project
moves to pydantic-ai v2.
