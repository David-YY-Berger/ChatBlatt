# Person Disambiguation

Source of truth: `backend_pipeline/data_pipeline/entity_resolution/PersonDisambiguator.py`
(module docstring is the authoritative spec — read it for exact tie-break order; this is a
summary). Used by `DBPopulateEntityRelGraph` for every extracted Person mention.

## Why it exists

A freshly extracted Person mention has no metadata of its own — just a name. Several real
people can share a `display_en_name` (two kings named Joash). `find_existing_person_key`
decides which existing DB entity (if any) the mention is, using only what the *current
source* says about it, compared with what the *DB already knows* about each same-named
candidate.

## `find_existing_person_key(entity, PersonSourceContext)`

1. Candidates = every `EPerson` with the **exact same `display_en_name`** (not
   `all_en_names`).
2. No candidates → `None` (new entity).
3. Drop any candidate the source **contradicts**:
   - the passage names a father/mother and the candidate's known one (from DB rels) differs;
   - source is Tanach and the candidate's `timePeriod` is Tanaim/Amoraim, or it has role
     Tanna/Amora.
4. None left → `None` (a different person than every existing one).
5. Exactly one left → that one, even with zero positive evidence.
6. Two+ left → `decide_entity`.

## `decide_entity` — narrows step by step, stops at one candidate

Each step keeps only its best-scoring candidates (a step with no signal is a no-op, everyone
moves on):

1. Most relationships in common with the mention (same type + direction + other entity);
   ties broken by: a shared Person link first, then a shared Place link.
2. Most related entities (via any DB rel) that this source also mentions.
3. Tanach sources only: candidate(s) **known to appear** in this source's book.
4. Fallback, by prominence: known in this book → most mentions in it → known in this source
   type → most mentions in it → most mentions overall → most relationships. Remaining ties →
   lowest key (earliest created — pre-populated entities win).

"Known to appear in" a book = `book_references` ∪ books of every source whose
`SourceMetadata.entity_keys` lists the candidate. `book_references` is never treated as
complete — a missing book is not a contradiction, just no evidence.

## Name matching (for "other entities" in steps 1–2, and father/mother contradiction)

`display_en_name` + `all_en_names`, case-insensitive, leading "the" ignored, `"A / B"`
treated as two alternative names, a bare name matches a qualified one (`"Ahaziah"` ~
`"Ahaziah of Judah"`, `"Nahash"` ~ `"Nahash (textual variant)"`) — two *differently*-qualified
names never match each other.

## Logging & caching

Every non-trivial decision prints with prefix `[PersonDisambiguation]`. Names/types of
*related* entities are cached for the instance's lifetime (existing entities are never
mutated by the populator); a candidate's own relationships/source mentions are re-read every
time, since each processed source adds to them.

## What this means for pre-population

A pre-populated person is found **only** through: its exact `display_en_name`, its DB
relationships (both directions) and the names on their other side, its `timePeriod`/`roles`,
and its `book_references`. That is exactly the data `entity_prepopulation.md` must supply.
