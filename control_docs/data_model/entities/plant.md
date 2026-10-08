# EPlant

Source of truth: `backend/models_db/EntityObjects/EPlant.py`.

Edible and inedible plants (e.g. Grape, Fig, Cedar, Hyssop, Apple, Wheat, Olive) — normalized,
singular, specific form. "Grape vine", "Grape tree", "Grape" should all just be "Grape".

## Fields

No type-specific db fields beyond the base `Entity`. No relationships for Plant entities
(no transient relationship fields beyond `comparedTo`/`contrastedWith`).

## Identity / dedup

Uses the base `Entity` behavior unmodified: `(display_en_name, entityType)`. Use
`try_insert_entity`.

## Overlap with Food

An entity can legitimately appear in both `Plant` and `Food` (e.g. Apple) — no
mutual-exclusion validator between these categories, unlike `Symbol` (see `symbol.md`).
