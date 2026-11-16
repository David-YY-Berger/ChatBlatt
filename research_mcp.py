"""Read-only MCP interface to the research features of Eitz Habina."""

from __future__ import annotations

import functools
import logging
import os
import threading
from dataclasses import asdict
from difflib import SequenceMatcher
from typing import Annotated, Literal

from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field

from backend.app.controllers.entity_populator import AS_TERM1, AS_TERM2, get_populator
from backend.app.controllers.entity_search.entity_search_controller import get_entity_search_handler
from backend.app.controllers.genealogy_tree_controller import GenealogyTreeController
from backend.app.controllers.number_search_controller import _parse_number_value
from backend.app.logic.lineage_logic import lineage_path, load_lineage_graph
from backend.app.logic.number_search_logic import NumberSearchLogic
from backend.app.logic.number_validation import number_error
from backend.app.logic.places_visited_logic import build_rows, load_options_and_relationships
from backend.app.SourceSearchHandler import SourceSearchHandler
from backend.app.SourceSearchQuery import SourceSearchQuery
from backend.common.miscFuncs import MixedLanguageQueryError, detect_query_language
from backend.db.DBFactory import DBFactory
from backend.models_db.Enums import EntityType, PassageType, RelType, SourceType
from backend_pipeline.data_pipeline.populator_scripts.merge_scripts.merge_candidates import (
    spelling_signature, split_title_prefix,
)
from system_common.UrlPaths import page_url

log = logging.getLogger(__name__)
_similarity_lock = threading.Lock()
EntityTab = Literal["people", "places", "nations", "tribes", "numbers", "animals", "foods", "plants"]
PageSize = Annotated[int, Field(ge=1, le=50)]
Offset = Annotated[int, Field(ge=0)]
BLOCKED_RELS = {RelType.studiedFrom, RelType.disagreedWith}
DETAIL_TABS = {"people", "places", "nations", "tribes"}
VISIBLE_TYPES = {
    EntityType.EPerson, EntityType.EPlace, EntityType.ENation, EntityType.ETribeOfIsrael,
    EntityType.ENumber, EntityType.EAnimal, EntityType.EFood, EntityType.EPlant,
}
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)

mcp = FastMCP(
    "Eitz Habina",
    instructions=(
        "Search authentic Jewish sources. Entity names are suggestions, not identity claims: "
        "disambiguate using metadata and keys. Sources have Hebrew and English text; ask which "
        "language the user wants before retrieving full text. Search results are ranked rather "
        "than filtered by similarity. Use relationship keys to retrieve supporting sources. "
        "Studied-from and disagreed-with data are excluded due to a data-quality warning."
    ),
    host="127.0.0.1",
    port=8502,
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["eitz-habina-prod.up.railway.app", "eitz-habina-prod.up.railway.app:*",
                       "localhost:*", "127.0.0.1:*"],
        allowed_origins=["https://eitz-habina-prod.up.railway.app"],
    ),
)


class InputError(ValueError):
    pass


def safe_tool(func):
    """Keep backend exception messages, which may contain secrets, out of MCP responses."""
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InputError:
            raise
        except Exception as exc:
            log.error("Research tool failed: %s (%s)", func.__name__, type(exc).__name__)
            raise RuntimeError("The research service could not complete the request. Please try again later.") from None
    return wrapped


def db():
    if os.environ.get("EITZ_DB_READ_ONLY", "").lower() != "true":
        raise RuntimeError("The MCP requires read-only database mode.")
    return DBFactory.get_prod_db_mongo()


def window(items: list, offset: int, limit: int) -> dict:
    return {
        "items": items[offset:offset + limit],
        "total": len(items),
        "offset": offset,
        "next_offset": offset + limit if offset + limit < len(items) else None,
    }


def source_summary(source) -> dict:
    return {
        "key": source.key, "title_en": str(source), "title_he": source.to_heb_str(),
        "summary_en": source.summary_en, "summary_he": source.summary_heb,
        "passage_types": [pt.name for pt in source.passage_types],
    }


def options(tab: str):
    return get_entity_search_handler(tab, db=db()).get_select_options()


def option_dict(option) -> dict:
    return option.model_dump(mode="json", exclude_none=True, exclude={"entity_keys"})


def entity_for(key: str, expected: set[EntityType] = VISIBLE_TYPES):
    entity = db().get_entity_by_key(key)
    if entity is None or entity.entityType not in expected:
        raise InputError("Entity key not found for the requested visible entity type. Use find_entities first.")
    return entity


def checked_rels(keys: list[str]):
    rels = db().get_rels_by_keys(keys)
    if len(rels) != len(set(keys)) or any(rel.rel_type in BLOCKED_RELS for rel in rels):
        raise InputError("Relationship keys must identify available, non-excluded relationships.")
    endpoints = db().get_entities_by_keys(list({k for rel in rels for k in (rel.term1, rel.term2)}))
    if len(endpoints) != len({k for rel in rels for k in (rel.term1, rel.term2)}) or any(
        entity.entityType not in VISIBLE_TYPES for entity in endpoints
    ):
        raise InputError("Relationship keys must identify available, non-excluded relationships.")
    by_key = {entity.key: entity for entity in endpoints}
    for rel in rels:
        visible = False
        for key, direction in ((rel.term1, AS_TERM1), (rel.term2, AS_TERM2)):
            populator = get_populator(by_key[key].entityType)
            if populator and populator.get_rel_field_map().get((rel.rel_type, direction)) not in (
                None, "studiedFrom", "taught", "disagreedWith", "symbolsAssociated"
            ):
                visible = True
        if not visible:
            raise InputError("Relationship keys must identify available, non-excluded relationships.")
    return rels


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def find_entities(
    entity_type: EntityTab,
    name: Annotated[str, Field(max_length=100)] = "",
    offset: Offset = 0,
    limit: PageSize = 20,
    is_woman: bool | None = None,
    is_non_jew: bool | None = None,
    is_group: bool | None = None,
    roles: list[str] | None = None,
    time_periods: list[str] | None = None,
    place_types: list[str] | None = None,
) -> dict:
    """Find visible entity options by name, aliases and approximate transliteration; return metadata and stable keys.

    Omit name to list options, optionally filtered by metadata.
    People filters use is_woman, is_non_jew, is_group, roles (Prophet, King, Judge,
    Kohen, Tanna, Amora), and time_periods (Tanach, Tanaim, Amoraim, No Time Period).
    Place filters use place_types. Filters of different kinds are combined; values
    within a list match any. Approximate matches are candidates, not proof of identity.
    """
    from backend.models_db.Enums import PlaceType, RoleType, TimePeriod

    name = name.strip()
    people_filters = any(v is not None for v in (is_woman, is_non_jew, is_group, roles, time_periods))
    if people_filters and entity_type != "people" or place_types is not None and entity_type != "places":
        raise InputError("Person metadata filters require people; place_types requires places.")
    for values, enum in ((roles, RoleType), (time_periods, TimePeriod), (place_types, PlaceType)):
        if values and any(v not in {e.value for e in enum} for v in values):
            raise InputError(f"Invalid filter. Allowed values: {', '.join(e.value for e in enum)}")
    query = name.casefold()
    sig = spelling_signature(split_title_prefix(query)[1])
    matches = []
    for option in options(entity_type):
        if any(value is not None and getattr(option, attr, None) != value for attr, value in (
            ("isWoman", is_woman), ("isNonJew", is_non_jew), ("isGroup", is_group)
        )):
            continue
        if roles and not set(roles).intersection(r.value for r in option.roles):
            continue
        if time_periods and (option.timePeriod is None or option.timePeriod.value not in time_periods):
            continue
        if place_types and (option.placeType is None or option.placeType.value not in place_types):
            continue
        names = [option.display_en_name, option.display_heb_name, *option.all_en_names, *option.all_heb_names]
        score = 1.0 if not query else 0.0
        for candidate in filter(None, names):
            candidate = candidate.casefold()
            candidate_sig = spelling_signature(split_title_prefix(candidate)[1])
            if candidate == query:
                score = max(score, 1.0)
            elif query in candidate:
                score = max(score, 0.95)
            elif sig == candidate_sig:
                score = max(score, 0.92)
            elif len(query) >= 3:
                score = max(score, SequenceMatcher(None, sig, candidate_sig).ratio())
        if score >= 0.6:
            matches.append((score, option))
    matches.sort(key=lambda item: (-item[0], item[1].display_en_name, item[1].key))
    return window([{"match_score": round(score, 3), **option_dict(opt)} for score, opt in matches], offset, limit)


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def get_entity(entity_type: Literal["people", "places", "nations", "tribes"], key: str,
               offset: Offset = 0, limit: PageSize = 20) -> dict:
    """Get visible entity details and paginated relationships, including keys for search_sources."""
    handler = get_entity_search_handler(entity_type, db=db())
    entity = entity_for(key, {handler.get_entity_type()})
    rels = [r for r in db().get_rels_for_entity(key) if r.rel_type not in BLOCKED_RELS]
    endpoints = db().get_entities_by_keys(list({k for r in rels for k in (r.term1, r.term2)}))
    visible = {e.key for e in endpoints if e.entityType in VISIBLE_TYPES}
    rels = [r for r in rels if r.term1 in visible and r.term2 in visible]
    populator = get_populator(entity.entityType)
    if populator:
        entity = populator.populate(entity, rels, db())
    entries = []
    for field, _ in handler.get_transient_field_labels():
        if field in {"studiedFrom", "taught", "disagreedWith", "symbolsAssociated"}:
            continue
        for label in getattr(entity, field, []):
            link = entity.rel_links.get(label)
            if not link or link[1] not in VISIBLE_TYPES:
                continue
            entries.append({
                "field": field, "name_en": label, "entity_key": link[0],
                "name_he": entity.rel_heb_names.get(link[0], ""),
                "roles": entity.rel_roles.get(link[0], []),
                "relationship_keys": entity.rel_keys_by_field.get(field, {}).get(label, []),
                "sources_available_via": "search_sources",
            })
    return {
        "key": key, "name_en": entity.display_en_name, "name_he": entity.display_heb_name,
        "metadata": handler.get_db_field_display(entity),
        "url": page_url(entity_type, {"id": key}),
        "relationships": window(entries, offset, limit),
    }


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def search_sources(
    text: Annotated[str, Field(max_length=1000)] = "",
    entity_keys: list[str] | None = None,
    relationship_keys: list[str] | None = None,
    match_all_entities: bool = False,
    source_types: list[Literal["TN", "BT"]] | None = None,
    passage_types: list[Literal["LAW", "STORY_TANACH", "STORY_SAGES", "PHILOSOPHIC", "GENEALOGY", "PROPHECY"]] | None = None,
    offset: Offset = 0,
    limit: PageSize = 20,
) -> dict:
    """Search source summaries. Text must be Hebrew OR English, never both.

    Text similarity reorders structural matches; it does not exclude unrelated
    sources. Entity keys are option keys from find_entities. Relationship keys
    come from get_entity or other research results. Full text is available
    separately via get_source_text in Hebrew or English.
    """
    text = text.strip()
    try:
        detect_query_language(text)
    except MixedLanguageQueryError as exc:
        raise InputError(str(exc)) from None
    entity_keys = entity_keys or []
    relationship_keys = relationship_keys or []
    if len(entity_keys) > 50 or len(relationship_keys) > 50:
        raise InputError("At most 50 entity keys and 50 relationship keys are allowed.")
    expanded = []
    for key in entity_keys:
        entity = entity_for(key)
        if entity.entityType == EntityType.ENumber:
            match = next((o for o in options("numbers") if o.key == key), None)
            if not match:
                raise InputError("Number keys must be option keys returned by find_entities.")
            expanded.extend(match.entity_keys)
        else:
            expanded.append(key)
    if relationship_keys:
        checked_rels(relationship_keys)
    selected_source_types = source_types or ["TN", "BT"]
    query = SourceSearchQuery(
        free_text_similarity=text, max_sources=limit, offset=offset,
        src_types=[SourceType[s] for s in selected_source_types],
        passage_types=[PassageType[p] for p in passage_types or []],
        entity_ids=expanded, rel_ids=relationship_keys, match_all_entities=match_all_entities,
    )
    db()
    with _similarity_lock:
        answer = SourceSearchHandler().get_answer_w_source_metadata(query)
    params = {"q": text, "ent": entity_keys, "rel": relationship_keys, "st": selected_source_types,
              "pt": passage_types or [], "entity_match": "all" if match_all_entities else ""}
    return {
        "items": [source_summary(s) for s in answer.src_metadata_lst], "total": answer.total_sources,
        "offset": offset, "next_offset": offset + limit if offset + limit < answer.total_sources else None,
        "url": page_url("source_search", params),
        "text_available": "Use get_source_text; English and Hebrew are available when present.",
        "similarity_note": "Text similarity ranks structural matches and does not filter them.",
    }


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def get_source_text(key: str, language: Literal["en", "he"],
                    offset: Offset = 0, max_characters: Annotated[int, Field(ge=1, le=10000)] = 5000) -> dict:
    """Retrieve a bounded chunk of one source's English or Hebrew text. Ask the user which language they want."""
    source = db().get_source_metadata_by_key(key)
    if source is None or source.source_type not in {SourceType.TN, SourceType.BT}:
        raise InputError("Source key not found in the available source types.")
    content = db().find_one_source_content(key)
    index = 0 if language == "en" else 1
    if len(content.content) <= index or not content.content[index]:
        raise InputError("The requested language is not available for this source.")
    text = BeautifulSoup(content.content[index], "html.parser").get_text(" ", strip=True)
    return {"source": source_summary(source), "language": language, "text": text[offset:offset + max_characters],
            "offset": offset, "total_characters": len(text),
            "next_offset": offset + max_characters if offset + max_characters < len(text) else None}


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def search_number(value: Annotated[str, Field(min_length=1, max_length=100)],
                  offset: Offset = 0, limit: PageSize = 20) -> dict:
    """Search a whole number greater than 1 or a nonzero fraction other than 1, e.g. 7 or 1/3; decimals and negatives are not accepted."""
    if not value.strip() or number_error(value):
        raise InputError("Enter a whole number greater than 1 or a fraction like 1/3: no negatives, decimals, zero numerator/denominator, or fractions equal to 1.")
    db()
    result = NumberSearchLogic().execute(_parse_number_value(value))
    rows = []
    if result:
        for category, occurrences in result.by_category.items():
            rows.extend({"category": category.value if category else None, **asdict(occ)} for occ in occurrences)
    return {**window(rows, offset, limit), "url": page_url("number_search", {"type": "number", "value": value}),
            "text_available": "Source keys can be used with get_source_text (English or Hebrew)."}


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def list_units(name: Annotated[str, Field(max_length=100)] = "", offset: Offset = 0, limit: PageSize = 20) -> dict:
    """List available English and Hebrew number units; optionally filter by part of a name."""
    db()
    units = NumberSearchLogic().list_units()
    rows = [{"unit_en": en, "unit_he": he} for en, he in units
            if not name or name.casefold() in (en or "").casefold() or name in (he or "")]
    return window(rows, offset, limit)


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def search_unit(unit: Annotated[str, Field(min_length=1, max_length=100)],
                offset: Offset = 0, limit: PageSize = 20) -> dict:
    """Search by an English unit name from list_units; return number occurrences and source keys."""
    if not unit.strip():
        raise InputError("Choose an English unit name from list_units.")
    db()
    result = NumberSearchLogic().execute_by_unit(unit.strip())
    rows = []
    if result:
        for row in result.rows:
            for category, occurrences in row.occurrences.by_category.items():
                rows.extend({"number": row.value, "category": category.value if category else None, **asdict(occ)}
                            for occ in occurrences)
    return {**window(rows, offset, limit), "url": page_url("number_search", {"type": "unit", "value": unit}),
            "text_available": "Source keys can be used with get_source_text (English or Hebrew)."}


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def places_visited(key: str, entity_type: Literal["people", "places"],
                   offset: Offset = 0, limit: PageSize = 20) -> dict:
    """Find visits, births and deaths for a person or place, with source summaries and relationship keys."""
    entity_for(key, {EntityType.EPerson if entity_type == "people" else EntityType.EPlace})
    people, places, rels = load_options_and_relationships(db())
    by_person = entity_type == "people"
    rows = build_rows(db(), key, by_person, rels, places if by_person else people)
    output = []
    for row in rows:
        keys = [r.key for r in rels if r.key and r.rel_type == row.rel_type and
                (r.term1, r.term2) == ((key, row.other.key) if by_person else (row.other.key, key))]
        output.append({"other": option_dict(row.other), "relationship_type": row.rel_type.value,
                       "relationship_keys": keys, "sources": [source_summary(s) for s in row.sources[:5]],
                       "source_count": len(row.sources), "more_sources": len(row.sources) > 5,
                       "sources_available_via": "search_sources"})
    return window(output, offset, limit)


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def family_tree(key: str, depth: Literal[1, 2] = 1, offset: Offset = 0, limit: PageSize = 20) -> dict:
    """Get a family graph as JSON, paginated by edges. Each edge includes relationship keys for sources."""
    entity_for(key, {EntityType.EPerson})
    graph = GenealogyTreeController(db=db()).get_genealogy_graph(key, depth)
    rels = db().get_rels_for_entities([n.key for n in graph.nodes])
    edges = []
    for edge in graph.edges:
        keys = [r.key for r in rels if r.key and r.rel_type.value == edge.rel_type and
                ((r.term1, r.term2) == (edge.from_key, edge.to_key) or
                 edge.rel_type == "spouseOf" and (r.term2, r.term1) == (edge.from_key, edge.to_key))]
        edges.append({**edge.model_dump(), "relationship_keys": keys, "sources_available_via": "search_sources"})
    selected = edges[offset:offset + limit]
    node_keys = {key} | {k for e in selected for k in (e["from_key"], e["to_key"])}
    return {"center_key": key, "nodes": [n.model_dump() for n in graph.nodes if n.key in node_keys],
            "edges": window(edges, offset, limit)}


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def lineage_candidates(start_key: str, direction: Literal["ancestors", "descendants"],
                       offset: Offset = 0, limit: PageSize = 20) -> dict:
    """List people reachable from a starting person in the chosen lineage direction."""
    entity_for(start_key, {EntityType.EPerson})
    graph = load_lineage_graph(db())
    predecessors = graph.paths_from(start_key, direction == "descendants")
    candidates = [option for key, option in graph.options.items() if key != start_key and key in predecessors]
    return window([option_dict(option) for option in candidates], offset, limit)


@mcp.tool(annotations=READ_ONLY)
@safe_tool
def lineage(start_key: str, target_key: str, direction: Literal["ancestors", "descendants"],
            offset: Offset = 0, limit: PageSize = 20) -> dict:
    """Find one shortest recorded parent-child line; return each step's relationship keys for source searches."""
    entity_for(start_key, {EntityType.EPerson})
    entity_for(target_key, {EntityType.EPerson})
    if start_key == target_key:
        raise InputError("Choose two different people.")
    graph = load_lineage_graph(db())
    predecessors = graph.paths_from(start_key, direction == "descendants")
    if target_key not in predecessors:
        return {"path": [], "steps": window([], offset, limit), "message": "No recorded line was found."}
    keys = lineage_path(predecessors, target_key)
    rels = db().get_rels_for_entities(keys)
    all_pairs = list(zip(keys, keys[1:]))
    steps = []
    for first, second in all_pairs[offset:offset + limit]:
        parent, child = (first, second) if direction == "descendants" else (second, first)
        steps.append({"from": first, "to": second,
                      "relationship_keys": [r.key for r in rels if r.key and r.term1 == child and r.term2 == parent
                                            and r.rel_type in {RelType.childOfFather, RelType.childOfMother}],
                      "sources_available_via": "search_sources"})
    page_keys = keys[offset:offset + limit + 1] if offset < len(all_pairs) else []
    return {"path": [option_dict(graph.options[k]) for k in page_keys],
            "steps": {"items": steps, "total": len(all_pairs), "offset": offset,
                      "next_offset": offset + limit if offset + limit < len(all_pairs) else None}}


if __name__ == "__main__":
    os.environ["EITZ_DB_READ_ONLY"] = "true"
    mcp.run("streamable-http")
