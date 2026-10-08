# ESymbol

Source of truth: `backend/models_db/EntityObjects/ESymbol.py`.

Specific symbolic objects/concepts with high significance (e.g. Ark of the Covenant,
Menorah, Tablets, Burning Bush), not generic objects used in imagery (sword, ox, garden)
unless they have a specific proper name.

## Fields

| Field | Notes |
|---|---|
| `symbolType` | `Optional[SymbolType]` |

`has_metadata()`: true once the base metadata (`display_heb_name`) **and** `symbolType` are set.

Transient relationship field (not persisted, filled in for the UI): `associatedWithPlace` —
see `ESymbol.TRANSIENT_DISPLAY_FIELDS`.

## Identity / dedup

Uses the base `Entity` behavior unmodified: `(display_en_name, entityType)`. Use
`try_insert_entity`.

## Extraction-time rule — never overlaps Animal/Food/Plant

`Entities.exclude_from_symbol_if_in_other_categories` (pydantic model validator) removes any
entity from `Symbol` that also appears in `Animal`, `Food`, or `Plant` in the same extraction
response — those categories take priority.
