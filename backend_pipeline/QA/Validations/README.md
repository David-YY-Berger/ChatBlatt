# Entity relationship validation scripts

Run these read-only checks from the `ChatBlatt` project root. They inspect the
production graph database and do not modify it.

| Script | Checks | Run |
|---|---|---|
| [`validate_entity_relationships.py`](validate_entity_relationships.py) | Reports `childOfFather` links whose known parent is female, `childOfMother` links whose known parent is male, pairs that are both siblings and parent/child (or reciprocal parent/child), and reciprocal `studiedFrom` links. Also reports a pair classified as both father and mother. Returns exit code 1 when it finds issues. | `python -m backend_pipeline.QA.Validations.validate_entity_relationships` |
| [`check_person_to_tribe_rels.py`](check_person_to_tribe_rels.py) | Lists all relationships whose second entity is a `TribeOfIsrael`, including relationships with an unexpected type. | `python -m backend_pipeline.QA.Validations.check_person_to_tribe_rels` |

Automated tests for the relationship validator are in
[`backend_pipeline/QA/Tests/test_entity_relationship_validations.py`](../Tests/test_entity_relationship_validations.py).

## Related validation code

[`backend/app/logic/number_validation.py`](../../../backend/app/logic/number_validation.py)
contains the number-search input validator; it is application logic, not a
standalone database validation script.
