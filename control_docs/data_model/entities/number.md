# ENumber

Source of truth: `backend/models_db/EntityObjects/ENumber.py`,
`backend/models_db/EntityObjects/NumberContext.py`,
`backend_pipeline/data_pipeline/populator_scripts/DBPopulateEntityRelGraph.py`
(`_is_ignored_number`), `frontend/pages/number_search.py` (`_validate_number`).

Explicit numeric values mentioned in the text (including fractions), e.g. "7 bulls", "40
years", "3.5 cubits". Not ordinals ("first", "2nd") and not vague counts ("a", "an", "each") —
filtered at the prompt level (`EntityRelGraphCaller`), not deterministically in code.

## Fields

| Field | Notes |
|---|---|
| `numberCategory` | `Optional[NumberCategory]` — `Sacrifice`/`Time`/`Money`/`People`/`Measurement`/`Obligation`/`Gematria`/`Misc` |
| `en_unit` / `heb_unit` | Normalized singular noun for what's counted/measured (e.g. "bull", "year", "silver") |
| `contexts` | `List[NumberContext]` — every passage context this number (same value+category+unit) was mentioned in, each tagged with the source keys it came from |

`has_metadata()`: overridden (not the base check) — true once `heb_unit` is set **and every**
context has a non-empty `heb_context`. Numbers never get a `display_heb_name`
(`heb_unit`/`heb_context` replace it).

## Identity / dedup — keys on more than just the name

`get_identity_tuple()`: `(entityType, display_en_name, numberCategory, en_unit.lower())` — the
same value in a different category or with a different unit is a **different** Number entity.
A repeat mention with the same value+category+unit is the same entity; the new mention's
context is merged in (`merge_contexts`), not duplicated.

`build_existence_query()` matches the same triple, with `en_unit` compared case-insensitively.

## DB write rule

Always `try_insert_number` (never plain `try_insert_entity`) — it merges the new mention's
context into an existing matching Number instead of creating a duplicate. See
`_insert_number` in `DBPopulateEntityRelGraph.py`.

## Deterministic exclusions (code, not pydantic)

Two rules are enforced in `DBPopulateEntityRelGraph._is_ignored_number` — deliberately in
plain populator code rather than a pydantic validator, so they apply uniformly regardless of
how the `NumberEntity` was constructed. A Number matching either rule is dropped the same way
as a non-proper-noun Person/Place: added to `ignored_entity_keys` (so relationships
referencing it are skipped too) and never inserted.

1. **Unit = "verse" (`_NUMBER_UNITS_TO_IGNORE`)** — a number whose `en_unit` is "verse" (e.g.
   "see verse 5") is a citation/cross-reference, not a true countable quantity.
2. **Value 0 or 1 (`_NUMBER_VALUES_TO_IGNORE`)** — checked against `display_en_name` (the
   normalized numeric string, e.g. `"1"` not `"1.0"`). `0` means nothing was counted; `1` is
   equivalent to "a"/"an" — no plurality worth recording as a standalone quantity. This
   applies regardless of unit, and regardless of whether the value arrived as a whole number
   or as a fraction that reduces to 1 (`_normalize_number_string` normalizes `"2/2"` → `"1"`
   before this check runs).

### Frontend mirror — number search

`frontend/pages/number_search.py`'s `_validate_number` rejects the same values at the UI
level so a user can't even attempt to search for them (they'd never match a stored entity
anyway): a whole-number input of `0` or `1`, or a fraction that reduces to 1 (numerator ==
denominator), both show `"❌ Number must be greater than 1 (0 and 1 are not allowed)"` /
`"❌ A fraction equal to 1 is not allowed (0 and 1 are not allowed)"`. If either exclusion
rule changes in `DBPopulateEntityRelGraph.py`, update this validation message too — it's a
UX mirror of the same rule, not independently sourced.
