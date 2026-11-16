# bs"d - lehagdil torah velahadir

from dataclasses import dataclass

from backend.models_db.Enums import RelType, SourceType
from backend.models_db.Rel import Rel
from backend.models_db.SourceClasses.SourceMetadata import SourceMetadata
from backend.models_dto.EntitySelectOption import EntitySelectOption

REL_TYPES = (RelType.visited, RelType.bornIn, RelType.diedIn)


@dataclass
class VisitRow:
    other: EntitySelectOption
    rel_type: RelType
    sources: list[SourceMetadata]


def load_options_and_relationships(db):
    """Only offer endpoints of correctly directed person-to-place relationships."""
    people = db.getPersonSelectOptions()
    places = db.getPlaceSelectOptions()
    person_keys = {option.key for option in people}
    place_keys = {option.key for option in places}
    rels = db.get_rels_by_type_for_entities(
        list(person_keys), [rel_type.value for rel_type in REL_TYPES],
        as_term1=True, as_term2=False,
    )
    rels = [rel for rel in rels if rel.rel_type in REL_TYPES
            and rel.term1 in person_keys and rel.term2 in place_keys]
    related_people = {rel.term1 for rel in rels}
    related_places = {rel.term2 for rel in rels}
    return ([option for option in people if option.key in related_people],
            [option for option in places if option.key in related_places], rels)


def build_rows(db, selected_key: str, by_person: bool,
               rels: list[Rel], other_options: list[EntitySelectOption]) -> list[VisitRow]:
    selected_rels = [rel for rel in rels
                     if (rel.term1 if by_person else rel.term2) == selected_key]
    if not selected_rels:
        return []
    other_by_key = {option.key: option for option in other_options}
    rel_keys = [rel.key for rel in selected_rels if rel.key]
    sources = db.get_source_metadata_filtered(rel_ids=rel_keys) if rel_keys else []
    sources_by_rel: dict[str, list[SourceMetadata]] = {}
    for source in sources:
        for rel_key in source.rel_keys:
            sources_by_rel.setdefault(rel_key, []).append(source)

    grouped: dict[tuple[str, RelType], dict[str, SourceMetadata]] = {}
    for rel in selected_rels:
        other_key = rel.term2 if by_person else rel.term1
        if other_key not in other_by_key:
            continue
        group = grouped.setdefault((other_key, rel.rel_type), {})
        for source in sources_by_rel.get(rel.key, []):
            group[source.key] = source

    rows = [
        VisitRow(other_by_key[other_key], rel_type,
                 sorted(source_map.values(), key=lambda source: (source.sort_key(), source.key)))
        for (other_key, rel_type), source_map in grouped.items()
    ]

    def row_sort_key(row: VisitRow):
        tanach = [source for source in row.sources
                  if source.source_type == SourceType.TN and source.get_book() is not None]
        first = min((source.sort_key() for source in tanach), default=None)
        return (first is None, first or (), row.other.display_en_name.casefold(),
                row.other.key, row.rel_type.value)

    return sorted(rows, key=row_sort_key)
