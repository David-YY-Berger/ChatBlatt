# EFood

Source of truth: `backend/models_db/EntityObjects/EFood.py`.

Edible items that act as food in the context of the passage (e.g. Bread, Manna, Wine, Grape,
Apple, Quail) — normalized, singular, specific form. Not: cow stomach used in an offering
(not acting as food), generic descriptions.

## Fields

No type-specific db fields beyond the base `Entity`. No relationships for Food entities
(no transient relationship fields beyond `comparedTo`/`contrastedWith`).

## Identity / dedup

Uses the base `Entity` behavior unmodified: `(display_en_name, entityType)`. Use
`try_insert_entity`.

## Overlap with Animal/Plant

An entity can legitimately appear in both `Food` and `Animal`/`Plant` (e.g. Apple, Quail) — no
mutual-exclusion validator between these categories, unlike `Symbol` (see `symbol.md`).
