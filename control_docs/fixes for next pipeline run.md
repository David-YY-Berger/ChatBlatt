# Fixes for next pipeline run

Improvements to make before re-running the whole population pipeline from scratch.

## 1. `personToTribeOfIsrael` rels resolve to the wrong entity (or are dropped)

**File:** `backend_pipeline/data_pipeline/populator_scripts/DBPopulateEntityRelGraph.py`
(`_try_insert_rel`, `_resolve_entity_key`, `_try_insert_cross_type_self_rel`)

**Problem:** Rel terms are resolved by *name only*. `_resolve_entity_key` loops over the categories
in `_CATEGORY_TO_ENTITY_TYPE` order and returns the first match, so `Person` wins over
`TribeOfIsrael`. For `Gershom -> Levi` (source `BT_Berakhot_0_7a:34-36`), `Levi` resolves to the
*Person* Levi, giving a person->person rel typed `personToTribeOfIsrael` instead of a rel to the
tribe entity. Only same-name pairs (`judah -> judah`) went through the cross-type branch
(`_try_insert_cross_type_self_rel`) and came out correct. Result in the DB: only ~31 person->tribe
rels where the person has the tribe's name, so most tribe memberships don't show in the UI.

**Fix:** Resolve each term using the type constraint of the rel type, not just the name.
`RELATIONSHIP_TYPE_CONSTRAINTS` (`PydanticModels/entity_rel_graph/response_models.py`) already maps
`personToTribeOfIsrael` to `("Person", "TribeOfIsrael")`. In `_try_insert_rel`, when the rel type has
a constraint, look up term1 in the constraint's first category and term2 in the second, using
`_lookup_typed_key(name, category, ...)`, falling back to the name-only lookup only if no constraint
exists. This also removes the need for the special same-name self-rel branch for constrained rel types.

**Related:** `Levites -> Levi` rels are not resolved because "Levites" is not a `Person` entity in the
DB (about 38 such cases in the backfill dry run). Decide whether groups like "Levites"/"priests" should
be kept as Person entities (so the rel can be stored) or dropped by the prompt/filter.

**Interim data fix:** `one_time_scripts/backfill_person_to_tribe_rels.py` backfills the missing rels
into the current DB. Not needed after a clean re-run with this fix. Stale person->person rels typed
`personToTribeOfIsrael` from the old logic stay in the current DB (a re-run from scratch removes them).

**Verify after fix:** run `one_time_scripts/check_person_to_tribe_rels.py`. It should list many
different people per tribe, not only same-name pairs.
