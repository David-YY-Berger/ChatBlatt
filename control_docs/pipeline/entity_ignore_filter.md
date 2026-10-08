# Entity Ignore Filter

Source of truth: `backend_pipeline/data_pipeline/PydanticModels/EntityIgnoreFilter.py`,
lists at `Paths.ENTITIES_TO_IGNORE_DIR` (`entities_to_ignore/Person`, `.../Place`).

## Purpose

The LLM extraction step sometimes returns a generic noun instead of a proper noun (e.g.
"the advisor", "the wilderness"). `is_ignored_entity_name(name, entity_type)` filters these
out before they become entities. Used by `DBPopulateEntityRelGraph` (dropped mentions never
reach `PersonDisambiguator`) and should be considered by any new code that creates
Person/Place entities from free text.

## Matching rules (type-specific — do not conflate them)

- **Person**: discarded if the name contains an ignore-list term **as a whole word**
  (case-insensitive, `\b`-delimited regex, compiled once and cached). **Not** a raw substring
  check — that would wrongly flag proper nouns that merely *contain* a term inside a longer
  word, e.g. "Manasseh" contains "man", "Amalek" contains "male", "Haman"/"Naaman" contain
  "man". None of those are the generic word itself, so none are filtered. "King Ahaz" *is*
  correctly filtered (contains the standalone word "king").
  - ⚠️ History: this was a raw-substring check until it was fixed (word-boundary regex) —
    it had been silently dropping every "Manasseh" mention. If this file is touched again,
    re-verify with `Manasseh`/`Amalek`/`Haman`/`Naaman`/`Samson` (must stay NOT filtered) and
    `King Ahaz`/`the king`/`the advisor` (must stay filtered).
- **Place**: discarded only on an **exact** match (case-insensitive) — a place name that
  merely *contains* a term (e.g. "Wilderness of Sin") is kept, since it's still a proper noun.

## Companion fix (extraction prompt)

`EntityRelGraphCaller`'s system prompt now explicitly tells the LLM to strip titles/epithets
from `en_name` ("King Ahaz" → "Ahaz") — this reduces how often the Person filter's word-match
even needs to trigger, and keeps `en_name` consistent with how pre-population expects bare
names (`entity_prepopulation.md` §Names).

## Related but separate: Number exclusions

`ENumber` entities are filtered by a different, dedicated check
(`DBPopulateEntityRelGraph._is_ignored_number`) — a verse/citation unit, or value 0/1. Not
part of `EntityIgnoreFilter.py` and not file-list-driven. See `data_model/entities/number.md`.

## Consequence for pre-population

An entity whose own name (or whose referenced name) collides with the filter is still
created, but every *future* passage mention of that name will be dropped before reaching the
disambiguator — the pre-populated entity becomes unreachable. Pre-population reports these
collisions; it does not change the filter itself (ask before editing the ignore lists or the
matching rule — it's shared by every populator run, past data may depend on current
behavior).
