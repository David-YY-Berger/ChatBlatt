# Part 6 — Observability and day-two operations

[Contents](README.md) · **Prerequisites:** none; Parts 1–2 for environment-specific
checks · **Effort:** 4–8 hours for a basic runbook · **Cost:** local tools and
existing free hosting logs

## The idea

**Logs** describe events; **metrics** summarize counts, durations or resource
usage over time; **traces** follow a request across components. A health check
answers a particular question: liveness (process works), readiness (can serve),
or a synthetic user journey (does a feature actually work?). An SLI measures
service behavior; an SLO is the desired target, not a provider SLA.

For a podcast: compare an app that is running but cannot reach Mongo with an app
whose homepage loads but similarity search is broken. Explain why analytics
about visitors is not a substitute for operational health.

## Exercises

1. Draw failure paths: Streamlit unavailable, DB unreachable/permission denied,
   incompatible data or missing GridFS index, slow model download/startup,
   search memory exhaustion, and a discontinued MCP endpoint. For each, identify
   an observable symptom, safe action and escalation decision.
2. Establish baseline measurements: startup/cold and warm search times, process
   memory after similarity search, DB storage/index growth, recent backup age,
   and chosen sample query results. Capture actual corpus size and provider limits.
   Optional local Python timing or OS tools are sufficient; no paid observability
   stack is required.
3. Consider structured, privacy-conscious app logs: environment, component,
   event/outcome, elapsed time and a non-sensitive correlation ID. Don't log
   credentials, Mongo URIs, raw searches, passage content, personal data or full
   query URLs. Explicitly surface errors without dumping raw secrets. Review
   retention and access. Preserve the existing GA4 opt-out and privacy rules.
4. Define a small manual smoke suite with expected outcomes for home, bilingual
   source search including similarity, entity/number, tree, PDF and shared links.
   Use known fixture data locally; for production use safe read-only examples and
   respect analytics opt-out. Check MCP only if it remains deployed.
5. Set modest proposed SLOs only after baselining, e.g. availability measured by
   successful scheduled synthetic checks and a percentile latency over a stated
   period. Define sampling frequency, denominator and exclusions, and acknowledge
   cold starts/sleep and free-host limitations. No external monitoring provider is
   guaranteed free forever; a manual scheduled check is a valid $0 first step.
6. Practice a non-production incident: make the fixture DB unavailable, observe
   symptoms, diagnose, restore connectivity and repeat the smoke suite. Keep a
   short runbook with checks, backup age, rollback steps, and known limitations.
   Part 2 covers a separate restore drill.

## Done when

You have recorded a baseline, detected and recovered from a staged DB outage, and
can tell the difference between process health and successful search. No sensitive
queries or credentials appear in the sampled logs. Existing GA4 reports remain
separate from these operational measurements.

**References:** [existing metrics and privacy](../frontend/metrics.md);
[Streamlit status](https://docs.streamlit.io/deploy/streamlit-community-cloud/status);
[recovery plan](02-database.md).

## Eitz Habina context for a standalone podcast

Eitz Habina, also called ChatBlatt, is a Torah-source research website. It offers
Hebrew and English passage searches, searches for entities and numbers, and
relationship/tree views linked to supporting passages. An offline pipeline retrieves
Sefaria passages and uses language-model-assisted extraction, validation and review
to prepare metadata. The website reads the prepared data, whose metadata may contain
errors; it does not run the pipeline for each visitor.

The Python Streamlit app calls backend logic directly and reads MongoDB: `Sources`
contains passages, `Graphs` contains entities, relationships and passage metadata,
and `Faiss` contains FAISS semantic and BM25 keyword indexes. Tanach and Babylonian
Talmud are currently populated; Talmud Yerushalmi, Midrash and Mishna are planned.
As the corpus grows, storage, memory and search latency may change, so operational
measurements matter. The user intends to retire Railway and retain the Streamlit
website; the optional remote MCP server currently runs on Railway. The app already
has privacy-conscious GA4 usage analytics, but the proposed operational baselines,
smoke checks and incident exercises are not implied by those analytics.
