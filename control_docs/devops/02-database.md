# Part 2 — Database isolation, capacity and recovery

[Contents](README.md) · **Prerequisites:** none for design; Part 1 for hosted
staging · **Effort:** 1–3 days, especially the first restore drill · **Cost:** $0
using local Mongo and local storage

## The idea

Isolation has layers: distinct database **servers or clusters** provide a stronger
boundary than database names on the same cluster; distinct identities and permissions
limit what each app can do. A **backup** is a copy; a **restore drill** proves that a
usable copy can actually be recovered. An index is derived data, but if the app needs
it to search, the backup/release still needs a compatible index or a tested way to
rebuild it.

For a podcast: distinguish Mongo's cluster, logical database, collection, GridFS and
database role; describe why one correct-looking homepage cannot prove data recovery.

## Current state

`backend/db/DBFactory.py` constructs a URI for one hardcoded Atlas host; the app's
`get_prod_db_mongo()` uses `DB_READ_ONLY_USERNAME` and `DB_READ_ONLY_PASSWORD`.
Population credentials are separate and have write access. `DBapiMongoDB` is a
singleton, and its collection definitions bind `Sources`, `Graphs`, and `Faiss` by
name. App read connections do not create indexes. This requires an actual target
selection change, not merely a different deployment name. Review the existing
[safety rules](../conventions/safety_and_testing.md) before any DB work.

## Tasks

1. **Choose the boundary.** Start with a separate local Mongo instance for development
   and CI; optionally add a separate free Atlas cluster/project for hosted staging
   if eligible and the fixture fits. Verify current provider limits and account
   eligibility; don't assume another free cluster is available. If hosted staging
   must temporarily share a cluster, use *different logical DB names and scoped
   users*, explicitly configure all three DB mappings, and recognize the weaker
   isolation, shared quota and configuration-error risk. Do not label same database
   names with a different login as isolation.
2. **Design configuration.** Select an explicit non-secret environment and Mongo
   target/URI per deployment; store credentials in the host's secret manager, not
   Git, test artifacts, command lines or logs. Support a local `mongodb://` target
   and Atlas SRV as appropriate. Validate missing/invalid settings and fail closed;
   preserve existing production behavior deliberately during migration. Do not infer
   target from `admin`, host name, or a credential's name.
3. **Enforce identity.** Production and staging app users get only needed read
   permissions on their own `Sources`, `Graphs`, `Faiss` and GridFS collections.
   Local fixture loading gets a separate writer scoped to test only. Ensure neither
   CI nor staging receives the production writer. Deny a staging credential against
   production and deny the app reader insert/update/delete/index creation; run
   write-denial probes only against disposable data with explicit authorization.
4. **Account for the singleton.** Avoid changing target inside a running app process;
   restart per environment. Make tests use separate processes or a safely resettable
   injected client. Add tests proving distinct targets and that missing config,
   unexpected environment, and production-target use in destructive test setup fail
   before connection or writes. Address every app call to `get_prod_db_mongo()` and
   ensure other consumers retain their intended behavior.
5. **Create a small, synthetic fixture** with linked source passages, metadata,
   entities and relationships, English/Hebrew, and relevant search indexes in both
   languages. Avoid copying real/private data or committing large DB dumps. Include
   representative TN/BT now; later add representative JT/MD/MS and verify book and
   source-type UI support independently of whether documents exist. If FAISS/BM25
   fixture creation is too heavy, separate an explicitly skipped search test from
   the core fixture and report the gap; do not pretend semantic search was tested.
6. **Measure before new corpora.** Record actual logical/physical sizes, collection
   and GridFS/index sizes as available, app/model memory, cold-start time, query
   latency, connection counts and source coverage. Compare against current provider
   limits with headroom; forecast with observed per-corpus growth, not a guess.
   Mongo free clusters currently advertise 512 MB; check how the provider measures
   the enforced limit. If it won't fit, choose a smaller permitted dataset or a
   deliberately different hosting design; this plan does not make unlimited data free.

## Recovery exercise

Before any destructive repopulation or migration, agree on acceptable **RPO** (how
much data loss, measured in time) and **RTO** (time to recover). Take a consistent
backup across all three logical DBs and both GridFS buckets; quiesce writes or use a
documented snapshot method that really supports the selected tier. Independently
dumping collections during active writes is not necessarily a coherent snapshot.
Record timestamp, code/schema version, Mongo/tool versions and dataset/index version.

Encrypt and keep at least one separate local/off-machine copy where appropriate;
verify storage permission and disk space. Check backup licensing/privacy and avoid
publishing dumps. Atlas Free backups are not a generally available dependable
fallback: its documented snapshot capability is private preview. Restore **only**
to a verified disposable local target, never production; inspect destination before
any restore and do not use destructive options against a real DB. Compare counts and
representative linked keys, indexes and GridFS, then exercise both-language source,
entity/relationship and similarity searches. Record actual RTO and whether the copy
meets RPO. Repeat after significant data/schema changes. MongoDB notes Windows
case-insensitive filesystems can overwrite case-differing collection names; use
archive format where applicable and verify server/tool version compatibility.

## Done when

An isolated fixture-backed app/test run succeeds without production secrets; wrong
targets and prohibited operations fail; a reader cannot write; a restoration to a
disposable target proves linked data and search work. Publish measured capacity and
document any unavailable full-index or hosted-staging checks explicitly.

**References:** [Atlas Free limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/);
[Atlas pricing](https://www.mongodb.com/pricing);
[mongodump behavior](https://www.mongodb.com/docs/database-tools/mongodump/mongodump-behavior/);
[MongoDB read roles](https://www.mongodb.com/docs/manual/reference/built-in-roles/).

## Eitz Habina context for a standalone podcast

Eitz Habina, also called ChatBlatt, is a Streamlit research website for Torah
sources. A user can search Hebrew and English passages, explore entities such as
people and places, find numbers, and view relationships or trees connected to
supporting sources. Its offline pipeline fetches Sefaria passages and uses
language-model-assisted extraction, validation and review to prepare metadata;
visitors use the prepared data, not the pipeline. Extracted metadata can contain
errors.

The Python app directly queries three logical MongoDB databases on one deployment:
`Sources` stores passages; `Graphs` stores entities, relationships and passage
metadata linking them; `Faiss` stores FAISS semantic and BM25 keyword indexes in
GridFS. All three are needed for a representative recovery and some searches need
compatible indexes. Today the populated corpus is Tanach and Babylonian Talmud;
Talmud Yerushalmi, Midrash and Mishna are planned, increasing potential storage and
memory needs. The Streamlit testing site currently shares the real database.
Separate test and production targets, synthetic fixtures and a rehearsed restore
are proposed improvements, not features already in place. The owner plans to
retire Railway and keep the Streamlit website; MCP is optional.
