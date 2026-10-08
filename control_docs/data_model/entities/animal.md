# EAnimal

Source of truth: `backend/models_db/EntityObjects/EAnimal.py`.

Real and mythical animals (e.g. Lion, Eagle, Serpent, Leviathan, Balaam's Donkey) — includes
talking animals that were previously classified under Person.

## Fields

No type-specific db fields beyond the base `Entity`.

Transient relationship field (not persisted, filled in for the UI): `spokeWith` — Animal can
**only** participate in the `spokeWith` relationship (Person↔Animal, Animal↔Animal). See
`EAnimal.TRANSIENT_DISPLAY_FIELDS`.

## Identity / dedup

Uses the base `Entity` behavior unmodified: `(display_en_name, entityType)`. Use
`try_insert_entity`.

## Overlap with Food/Plant

An entity can legitimately appear in both `Animal` and `Food` (e.g. Quail) — no
mutual-exclusion validator between these two, unlike `Symbol` (see `symbol.md`).
