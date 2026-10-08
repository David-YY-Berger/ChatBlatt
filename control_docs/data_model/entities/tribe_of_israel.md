# ETribeOfIsrael

Source of truth: `backend/models_db/EntityObjects/ETribeOfIsrael.py`.

Fixed set of 13 tribes (not extended from sources — see the `# DEFINED` comment at the
bottom of the source file).

## Fields

No type-specific db fields beyond the base `Entity`.

Transient relationship field (not persisted, filled in for the UI): `membersOfTribeIsrael`
(Tribe → Person/Group) — see `ETribeOfIsrael.TRANSIENT_DISPLAY_FIELDS`.

## Identity / dedup

Uses the base `Entity` behavior unmodified: `(display_en_name, entityType)`. Use
`try_insert_entity`.

## Extraction-time rule — auto-overlap with Person

`Entities.ensure_entity_overlap` (pydantic model validator, `entity_models.py`) auto-adds any
`TribeOfIsrael` entity to `Person` too if it isn't already there (tribes are named after
people), so relationships like `childOfFather`/`bornIn` work for tribe patriarchs.

## Extraction-time rule — must be a known tribe

`Entities.validate_tribes` (pydantic field validator) filters out any `TribeOfIsrael` entity
whose name isn't in the known 13-tribe list (`TRIBES_OF_ISRAEL` in `erg_constants.py`).
