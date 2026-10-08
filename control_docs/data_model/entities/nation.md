# ENation

Source of truth: `backend/models_db/EntityObjects/ENation.py`.

## Fields

No type-specific db fields beyond the base `Entity`.

Transient relationship fields (not persisted, filled in for the UI): `personsBelongTo`,
`placesIn`, `enemyOf`, `allyOf`, `comparedTo`, `contrastedWith` — see
`ENation.TRANSIENT_DISPLAY_FIELDS`.

## Identity / dedup

Uses the base `Entity` behavior unmodified: `(display_en_name, entityType)`. Use
`try_insert_entity`.

## Extraction-time rules

- **Demonym → nation conversion** (`Entities.convert_demonyms_to_nations`, pydantic model
  validator): "Aramean" → "Aram", etc. (`DEMONYM_TO_NATION` in `erg_constants.py`). The
  extraction prompt also instructs the LLM to always use the nation name, not the demonym, so
  this is a safety net, not the primary mechanism.
- **Generic-word filter** (`Entities.validate_proper_nouns`, pydantic field validator): drops
  entries like "nation", "enemy", "kingdom", "tribe" (generic, not a proper noun) — exact
  match against a hardcoded word set, not word-boundary/substring like the Person/Place
  ignore-list filter (`pipeline/entity_ignore_filter.md`).
