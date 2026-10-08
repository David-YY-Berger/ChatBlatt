# EPlace

Source of truth: `backend/models_db/EntityObjects/EPlace.py`.

## Fields

| Field | Notes |
|---|---|
| `placeType` | `Optional[PlaceType]` |

`has_metadata()`: true once the base metadata (`display_heb_name`) **and** `placeType` are set.

Transient relationship fields (not persisted, filled in for the UI): `personsDiedIn`,
`personsBornIn`, `personsVisited`, `personsPrayedAt`, `personsAssociated` (reverse of
`associatedWithPlace`), `symbolsAssociated` (reverse of Symbol→Place), `inNation`,
`comparedTo`, `contrastedWith` — see `EPlace.TRANSIENT_DISPLAY_FIELDS` for the UI's canonical
order.

## Identity / dedup

Uses the base `Entity` behavior unmodified: `(display_en_name, entityType)`. Use
`try_insert_entity` — safe for Place (unlike Person, two same-named places are the same place).

## Extraction-time filtering

A Place mention that **exactly matches** (case-insensitive) a generic/non-proper-noun term
(e.g. "the wilderness") is dropped. Unlike Person, this is an exact match only — a place name
that merely *contains* a term (e.g. "Wilderness of Sin") is kept, since it's still a proper
noun. See `pipeline/entity_ignore_filter.md`.
