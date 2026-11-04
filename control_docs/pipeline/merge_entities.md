# Entity Merging

Three pieces, all merging **by entity key** through one shared `EntityMerger`:
1. `DBPopulateMergeEntities` - hand-written CSVs (name -> keys, then merge).
2. `merge_scripts/DBIdentifyPersonMergeCandidates` - read-only, writes review `.md` files.
3. `merge_scripts/DBApplyMergeDecisions` - merges the groups a human ticked.

## CSV merger: `DBPopulateMergeEntities`

Script: `populator_scripts/DBPopulateMergeEntities.py`, entry `test_merge_entities`. Pipeline step 5.
Input (`Paths.MERGE_CSV_DIR`): `populator_scripts/entitys_to_merge/<entityType lowercased>_to_merge.csv` (`person_to_merge.csv`,
`place_to_merge.csv`; missing file = nothing to do, unknown filename = warning + skipped).

CSV columns: `final_display_name`, `display_names_to_join` (`|`-separated `display_en_name`s,
case-insensitive), `merged` (`1` once done; the CSV is rewritten after every row, so reruns resume).
A headerless CSV is accepted (assumed column order, warning); blank rows dropped.

Per not-yet-merged row:
1. Each name is looked up by exact case-insensitive `display_en_name`, **restricted to the file's
   type**. A name matching **more than one** entity => row is `ambiguous`, logged, skipped, nothing
   changed. (Hence it cannot merge same-named duplicates or `rabbi X` + `X` when `X` itself is duplicated.)
2. <2 distinct entities found => `nothing_to_merge`; `merged` left unset so a later run re-checks.
3. Target = the entity already named `final_display_name`, else the first found in column order.
   All others are duplicates.
4. `EntityMerger.merge_into_target` merges each duplicate one at a time, persisted step by step:
   - fold fields: target `display_en_name` := lowercased final name; `display_heb_name` filled if empty;
     `all_en_names` (+ dup display name + final name), `all_heb_names`, `alias_keys` (+ dup's key) unioned
     case-insensitively; `ENumber.contexts` merged; every other persisted field via reflection
     (lists unioned, bools OR'd, scalars fill-if-empty - target's value wins on conflict);
   - `update_entity(target)`;
   - every `Rel` of dup re-pointed to target via `try_insert_rel` (exact-triple dedup; **self-loops
     dropped**; note symmetric rels reversed are not detected as duplicates); `SourceMetadata.rel_keys`
     re-pointed (or removed if the rel was dropped); old rel deleted;
   - `SourceMetadata.entity_keys` re-pointed;
   - dup deleted.
5. Row marked `merged=1`, CSV rewritten. Per-row exceptions => `error`, run continues.
Not transactional across the steps; safety comes from ordering (dup stays valid until fully retired).
No name-matching beyond `display_en_name` (`all_en_names` is not searched).

## Candidate finders + apply (`populator_scripts/merge_scripts/`)

| File | Role |
|---|---|
| `EntityMerger.py` | Key-based merge engine (fold fields, re-point rels / SourceMetadata, delete dup); `choose_target` = entity already named like the final name, else most rels |
| `merge_candidates.py` | DB-free logic: prefix stripping, grouping, chunking, rendering, `parse_review_file`, `carry_over_decisions`, `select_groups_to_merge` |
| `DBIdentifyPersonMergeCandidates.py` | Read-only; `test_identify_prefix_matches`, `test_identify_same_name_matches` |
| `DBApplyMergeDecisions.py` | `test_apply_merge_decisions` - applies ticked decisions |
| `test_merge_candidates.py` | DB-free unit tests (run with the repo `venv`) |

Review files are grouped by match family under `Paths.MERGE_REVIEW_DIR`
(`.../real_data/merge_review/`): `prefix_matches/person_prefix_matches_NNN.md` and
`same_name_matches/person_same_name_matches_NNN.md` (EPerson only). Confidence files are stored
alongside the review files for their family. The identify jobs carry decisions forward from legacy
files previously stored directly in `MERGE_REVIEW_DIR`.

**Groups**
1. *prefix*: name minus a leading `rabbi|rabban|rebbi|rav|abba|reb|r.` is equal and the group has >=2
   distinct display names (`akiva` / `rabbi akiva` / `rav akiva`). Final name = the bare name. Edit `TITLE_PREFIXES` to add prefixes.
2. *same_name*: identical `display_en_name` on >=2 persons. Each entity lists type/period flags, roles,
   `book_references` (pre-populated = deliberately separate people, flagged) and all rels (`type -> other`
   outgoing, `other -> type` incoming). A `childOfFather`/`childOfMother`/`descendantOf` whose parent is
   God/Hashem gets a `WARNING` line.
3. *close spelling* (hanna/hana/hannah): TBD, not implemented.
A person with no candidates appears in no file. An entity can be in both a prefix and a same-name group.

**Identify runtime**: `max_entities_to_check` (setUp, default 50; `None` = all) limits how many persons (sorted by
name) are starting points - found groups are still complete. `max_entities_per_file` (default 100); a group is never split.

**Review format** (human + machine): `<!-- merge-group: {"id","kind","keys":[...]} -->`, then `- [ ] merge` and
`- [ ] dont merge`; tick one with `x`. Neither = undecided, both = conflict (conflict is never merged).

**Re-running identify is safe for decisions.** It reads the existing family files first and carries every tick
into the regenerated files when the group id AND the exact set of entity keys still match; previously ticked
groups not rediscovered (smaller limit) are kept if their entities still exist. Deliberately NOT carried: a group
whose membership changed (comes back unticked - re-review), and groups whose entities were merged away. Files are
rewritten/renumbered in place - so editing a file while a run is writing it, or deleting files you ticked, loses ticks.
Running with limit 50, ticking, then rerunning with 100 is fine.

**Apply** (`DBApplyMergeDecisions`): `dry_run` defaults to **True** (prints the plan). `undecided_policy`:
`"skip"` (merge only ticked `merge`) or `"merge"` (merge everything except `dont merge`/conflict; groups with a
pre-populated person are still skipped unless explicitly ticked). Per group all keys must still exist
(else `STALE`, skipped - e.g. already merged through another group); merge into the chosen target with the group
label as final name. Safe to re-run.
