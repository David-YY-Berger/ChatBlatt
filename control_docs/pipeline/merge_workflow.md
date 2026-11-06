# Merge Workflow - how to run it

Step-by-step runbook for merging duplicate **Person** entities via human-reviewed files.
Design details / internals: `merge_entities.md`. Paths come from `backend/common/Paths.py`
(`MERGE_REVIEW_DIR` = `ChatBlatt_data_files/real_data/merge_review/`).

> There is no test DB - the apply step writes to the real DB. Take a backup first
> (`Paths.DB_BACKUPS_DIR`) and read `conventions/safety_and_testing.md`.

All scripts are unittest-style: run one by clicking "Run" on the `test_*` method in the IDE, or from the repo
root with the repo venv:

```
venv\Scripts\python.exe -m unittest backend_pipeline.data_pipeline.populator_scripts.merge_scripts.<Module>.<Class>.<test_method>
```

## Overview

1. **Identify** (read-only) -> writes review `.md` files.
2. **Review** - you tick checkboxes in those files.
3. **Apply** (dry run first, then for real) -> merges by entity key.
4. Repeat with a bigger limit until everyone is covered.

## Step 1 - Identify candidates

Module `DBIdentifyPersonMergeCandidates`, class `DBIdentifyPersonMergeCandidates`:

| Test method | Finds | Output file |
|---|---|---|
| `test_identify_prefix_matches` | `akiva` / `rabbi akiva` / `rav akiva` (prefixes rabbi, rabban, rebbi, rav, abba, reb, r.) - most obviously mergeable | `prefix_matches/person_prefix_matches_NNN.md` |
| `test_identify_same_name_matches` | persons with identical display name, with all their relationships (God/Hashem-as-parent flagged) | `same_name_matches/person_same_name_matches_NNN.md` |

Settings (in `setUp`, or set as attributes before calling it):
- `max_entities_to_check` - default **50**: only the first 50 persons (alphabetical) are used as starting points.
  Set `None` to check everyone. Persons with no candidates are never written to a file.
- `max_entities_per_file` - default 100 (a group is never split across files).

Each run also writes a **confidence file** next to the review files, in the same family folder:
`prefix_matches/confidence_person_prefix_matches.md` /
`same_name_matches/confidence_person_same_name_matches.md`. It rates every group 0-100% (how likely all its entities are the same person),
sorted most confident first. Each row carries a machine-readable `<!-- merge-confidence: {"id", "confidence", "keys"} -->`
comment (read with `merge_candidates.parse_confidence_file`). For prefix groups, tick merge decisions in the
consolidated prefix confidence file; the per-chunk prefix files are detail-only. Same-name decisions remain in
their per-chunk files. Heuristic: weakest pair in the group wins;
a title-prefix/same-name base score is raised by shared Hebrew name/parents/relations and lowered by conflicting
gender/time period/isNonJew/isGroup, different parents, or pre-populated entities. Any group containing a member
with a role other than Tanna or Amora is rated 0%.

Start with the prefix test (50), review/apply, then raise the limit (e.g. 200, then `None`) and re-run.

## Step 2 - Review the files

Open the `.md` files in the corresponding match-family folder under `MERGE_REVIEW_DIR`. Prefix groups are detailed
in the chunk files and decided in the consolidated confidence file; same-name groups are both detailed and decided
in the chunk files. A group looks like:

```
## Group 3: "akiva" (3 entities)
<!-- merge-group: {"id": "prefix:akiva", "kind": "prefix", "keys": ["...", "..."]} -->
```

The prefix chunk files contain entity details only. In `confidence_person_prefix_matches.md`, each group has:

```markdown
3. **95%** "akiva" (3 entities) <!-- merge-confidence: {"id": "prefix:akiva", "confidence": 95, "keys": ["...", "..."]} -->
- [ ] merge
- [ ] dont merge
```

Tick **one** line by changing `[ ]` to `[x]` in that consolidated file. Do not edit the `<!-- ... -->` comment.
- Neither ticked = undecided. Both ticked = conflict (never merged).
- Merge only a few -> tick `merge` on those. Merge most -> tick `dont merge` on the exceptions and use
  `undecided_policy = "merge"` in step 3.
- Same-name groups are often genuinely different people (several Joashes) - compare relationships.
  Entities marked *Pre-populated* were deliberately created as separate people.

## Re-running identify (safe)

Re-running reads your existing files first and carries every tick over to the regenerated files if the group id
and its exact set of entity keys are unchanged; ticked groups the smaller/newer scan doesn't rediscover are kept.
A group whose membership changed returns **unticked** (re-review). Files are rewritten/renumbered in place, so
close them in your editor first and don't delete ticked files. Ticking 2 groups, then re-running with a bigger
limit and ticking one more, is fine. Existing ticks in prefix chunk files are migrated to the consolidated
prefix confidence file on the next identify run.

## Step 3 - Apply decisions

Module `DBApplyMergeDecisions`, class `DBApplyMergeDecisions`, method `test_apply_merge_decisions`. It reads prefix
decisions only from `prefix_matches/confidence_person_prefix_matches.md`; prefix chunk files are not decision inputs.
Same-name decisions continue to come from their chunk files.

1. **Dry run (default, `dry_run = True`)**: prints `[DRY RUN] <group>: merge [dup keys] into <target> as '<name>'`
   for every selected group. Nothing is written. Check the plan.
2. **Real run**: set `dry_run = False` (in `setUp`, or on the instance before `setUp()`) and run again.

Settings:
- `undecided_policy`: `"skip"` (default - merge only groups ticked `merge`) or `"merge"` (merge every group except
  those ticked `dont merge` / conflict; groups containing a pre-populated person are still skipped unless ticked `merge`).
- `review_dir` - defaults to `Paths.MERGE_REVIEW_DIR`.

Output tags: `MERGED`, `DRY RUN`, `STALE` (an entity no longer exists, e.g. already merged via another group - skipped),
`PROTECTED`, `ERROR`; ends with a `SUMMARY` line. Re-running is safe.

The merged entity keeps the group's name (bare name for prefix groups), gets every name/key as an alias, and
inherits all relationships and source references (self-loops dropped, duplicates de-duplicated).

## After applying

Re-run step 1 (same limit) - merged groups disappear from the files; remaining decisions stay.
Then optionally rebuild search indexes (`DBPopulateFaissAndBm25`) if entity names feed them.

## Other merge path (hand-written CSV)

`DBPopulateMergeEntities.test_merge_entities` merges by **name** from `populator_scripts/entitys_to_merge/<type>_to_merge.csv`
(`final_display_name,display_names_to_join,merged`). Use it for known aliases (e.g. `jacob|israel`); it skips
ambiguous names. Details in `merge_entities.md`.
