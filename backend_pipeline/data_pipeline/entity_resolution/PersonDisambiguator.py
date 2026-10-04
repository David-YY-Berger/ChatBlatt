# bs"d
"""
PersonDisambiguator - decides which existing DB Person (if any) a Person mention
extracted from a source refers to.

Several different people can share a display_en_name (e.g. Joash king of Judah and
Joash king of Israel, pre-populated as separate entities). A freshly extracted mention
has NO metadata of its own, so the only evidence is what its source says about it
(PersonSourceContext: its relationships in the passage, the other entities in the
passage, the passage's book), compared with what the DB knows about each same-named
candidate (its relationships, the entities it is related to, the sources that mention
it, its timePeriod/roles).

find_existing_person_key -> key of the entity to add the mention to, or None to create a new one:
  - No same-named candidate         -> None (new entity).
  - Drop every candidate the source CONTRADICTS:
      * the passage names a father/mother, the candidate has a known one, and they differ;
      * a Tanach source cannot be talking about someone known to be a Tanna/Amora.
  - None left                       -> None: a different person than every existing one.
  - Exactly one left                -> it: nothing indicates the mention is someone else.
  - Two or more left                -> decide_entity.

decide_entity narrows the remaining candidates step by step. Each step keeps only its
best-scoring candidates - if nobody scores above zero the step is no evidence, and all
move on - and stops as soon as one candidate is left:
  1. Most relationships in common with the mention (same rel type + direction + other
     entity); ties broken by relationships to a Person, then to a Place.
  2. Most related entities (through any DB relationship) that this source also mentions.
  3. Tanach sources only: the candidate(s) known to appear in this source's book.
  4. Fallback - the most prominent candidate: known to appear in this book, then most
     mentions in it; known to appear in this source type (TN/BT/...), then most mentions
     in it; then most mentions overall, then most relationships. Remaining ties go to the
     earliest created entity (so pre-populated entities win).

The books a candidate is "known to appear in" are its book_references (set only by the
initial pre-population of well-known entities) plus the books of the sources that mention
it (SourceMetadata.entity_keys - these grow as sources are processed). book_references are
never treated as complete, so a book missing from them is no contradiction.

Other entities are matched by name: display_en_name + all_en_names, case-insensitive,
ignoring a leading "the", treating "A / B" as two alternative names, and letting a bare
name match a qualified one ("Ahaziah" ~ "Ahaziah of Judah", "Nahash" ~ "Nahash (textual
variant)", "Jehoiada" ~ "Jehoiada the Priest").

Caching: names/types of related entities are cached for the lifetime of the instance
(the populator never modifies existing entities). Candidates' relationships and source
mentions are re-read for every decision, since each processed source adds to them.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from backend.db.data_names.Books import Books
from backend.models_db.EntityObjects.Entity import Entity
from backend.models_db.EntityObjects.EntityIdentity import PersonSourceContext
from backend.models_db.Enums import EntityType, RelType, RoleType, SourceType, TimePeriod
from backend.models_db.SourceClasses.SourceClass import SourceClass

_LOG_PREFIX = "  [PersonDisambiguation]"

# Relationship types where (A, B) states the same fact as (B, A).
_SYMMETRIC_REL_TYPES = frozenset({
    RelType.spouseOf, RelType.spokeWith, RelType.disagreedWith, RelType.enemyOf,
    RelType.allyOf, RelType.comparedTo, RelType.contrastedWith, RelType.AliasOf,
})
_PARENT_REL_TYPES = frozenset({RelType.childOfFather, RelType.childOfMother})

_TALMUDIC_TIME_PERIODS = frozenset({TimePeriod.Tanaim, TimePeriod.Amoraim})
_TALMUDIC_ROLES = frozenset({RoleType.Tanna, RoleType.Amora})

_NAME_QUALIFIERS = (" son of ", " daughter of ", " wife of ", " of ", " the ")


# ─── Name matching ────────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Lowercase, trim, collapse whitespace and drop a leading 'the '."""
    norm = " ".join(name.lower().split())
    return norm[4:] if norm.startswith("the ") else norm


def _name_head(norm_name: str) -> str:
    """
    The bare name without its qualifier: "ahaziah of judah" -> "ahaziah",
    "jehoiada the priest" -> "jehoiada", "zechariah (prophet)" -> "zechariah".
    Returns the name unchanged if it has no qualifier.
    """
    head = re.sub(r"\(.*?\)", " ", norm_name).split(",")[0]
    cuts = [head.find(q) for q in _NAME_QUALIFIERS if q in head]
    if cuts:
        head = head[:min(cuts)]
    return " ".join(head.split()) or norm_name


def _names_match(name: str, names: Set[str], heads: Set[str]) -> bool:
    """
    True if a passage name refers to an entity known by `names` (whose bare forms are
    `heads`): the same normalized name, or one side is the bare form of the other's
    qualified name. Two differently-qualified names ("children of israel" /
    "children of ammon") never match.
    """
    norm = _normalize_name(name)
    return norm in names or norm in heads or _name_head(norm) in names


def _rel_signature(rel_type: RelType, person_is_term1: bool) -> tuple:
    """
    Comparable form of "the person takes part in a rel_type relationship, on this side".
    Direction is dropped for symmetric types, and "the other is the person's child" is the
    same fact whether it was recorded as childOfFather or childOfMother.
    """
    if rel_type in _SYMMETRIC_REL_TYPES:
        return rel_type, None
    if rel_type in _PARENT_REL_TYPES and not person_is_term1:
        return "parentOf", None
    return rel_type, person_is_term1


_FATHER_SIGNATURE = _rel_signature(RelType.childOfFather, True)
_MOTHER_SIGNATURE = _rel_signature(RelType.childOfMother, True)


def _book_of(source_key: str) -> Tuple[str, str]:
    """(source type prefix, book name) of a source key, e.g. ("TN", "II Kings")."""
    return source_key[:2], SourceClass.get_book_name_from_key(source_key)


def _referenced_books(entity: Entity) -> Set[Tuple[str, str]]:
    """(source type prefix, book name) of every book in the entity's book_references."""
    books = (Books.get_by_db_name(name) for name in entity.book_references or [])
    return {(book.source_type.name, book.database_name) for book in books if book is not None}


# ─── What the DB knows ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _EntityInfo:
    """Name forms and type of a DB entity, for matching it against names from a passage."""
    display_name: str
    names: FrozenSet[str]  # normalized display_en_name + all_en_names
    heads: FrozenSet[str]  # bare forms of qualified names ("ahaziah of judah" -> "ahaziah")
    entity_type: EntityType

    @classmethod
    def from_entity(cls, entity: Entity) -> "_EntityInfo":
        # "Gideon / Jerubbaal" is known by the full form and by each alternative.
        raw_names = [entity.display_en_name, *entity.all_en_names]
        names = {_normalize_name(form) for name in raw_names if name
                 for form in (name, *name.split("/")) if form.strip()}
        heads = {_name_head(n) for n in names} - names
        return cls(entity.display_en_name, frozenset(names), frozenset(heads), entity.entityType)

    def matches(self, name: str) -> bool:
        return _names_match(name, self.names, self.heads)


@dataclass
class _Candidate:
    """An existing Person sharing the mention's display_en_name, plus what the DB knows about it."""
    entity: Entity
    related_by_signature: Dict[tuple, List[_EntityInfo]] = field(default_factory=dict)
    related_names: Set[str] = field(default_factory=set)
    related_heads: Set[str] = field(default_factory=set)
    relationship_count: int = 0
    # Loaded lazily, only when a decision gets past steps 1-2 (_load_appearances):
    source_keys: Optional[Set[str]] = None  # the sources mentioning it
    known_books: Optional[Set[Tuple[str, str]]] = None  # its book_references + the books of source_keys

    @property
    def key(self) -> str:
        return self.entity.key

    def add_relation(self, signature: tuple, other: _EntityInfo) -> None:
        self.related_by_signature.setdefault(signature, []).append(other)
        self.related_names |= other.names
        self.related_heads |= other.heads
        self.relationship_count += 1

    def is_related_to(self, name: str) -> bool:
        return _names_match(name, self.related_names, self.related_heads)

    def is_talmudic_sage(self) -> bool:
        roles = set(getattr(self.entity, "roles", None) or [])
        return getattr(self.entity, "timePeriod", None) in _TALMUDIC_TIME_PERIODS or bool(roles & _TALMUDIC_ROLES)


# ─── The disambiguator ────────────────────────────────────────────────────────

class PersonDisambiguator:
    """See module docstring. One instance per population run (it caches entity names)."""

    def __init__(self, db_api):
        self.db_api = db_api
        self._entity_info_cache: Dict[str, Optional[_EntityInfo]] = {}  # None = key not in the DB

    def find_existing_person_key(self, entity: Entity, ctx: PersonSourceContext) -> Optional[str]:
        """Key of the existing Person this mention refers to (add to it), or None (create a new entity)."""
        same_named = self.db_api.get_entities_by_display_en_name(entity.display_en_name, EntityType.EPerson)
        if not same_named:
            return None

        # Relationships are only needed to compare a passage father/mother, or to choose among 2+ candidates.
        with_relations = len(same_named) > 1 or bool(ctx.fathers or ctx.mothers)
        candidates = self._load_candidates(same_named, with_relations)

        contradictions = {c.key: reason for c in candidates if (reason := self._contradiction(ctx, c))}
        plausible = [c for c in candidates if c.key not in contradictions]

        if not plausible:
            self._log(entity, ctx, f"new entity - contradicts every existing candidate: {contradictions}")
            return None
        if len(plausible) == 1:
            if contradictions:
                self._log(entity, ctx, f"{len(candidates)} candidates -> {plausible[0].key}, "
                                       f"the only one not contradicted: {contradictions}")
            return plausible[0].key
        return self.decide_entity(entity, ctx, plausible)

    def decide_entity(self, entity: Entity, ctx: PersonSourceContext, candidates: List[_Candidate]) -> str:
        """Picks which of 2+ plausible same-named candidates the mention refers to (see module docstring)."""
        trail: List[str] = []  # scores of every step that gave evidence, for the decision log
        remaining = candidates

        # 1. Most relationships in common; ties broken by relationships to a Person, then to a Place.
        remaining = self._keep_best(remaining, "common relationships (total, with Person, with Place)",
                                    lambda c: self._common_relationships_score(ctx, c), trail)
        if len(remaining) == 1:
            return self._decided(entity, ctx, candidates, remaining[0], trail)

        # 2. Most related entities that this source also mentions.
        remaining = self._keep_best(remaining, "related entities mentioned in this source",
                                    lambda c: (self._related_entities_in_source(ctx, c),), trail)
        if len(remaining) == 1:
            return self._decided(entity, ctx, candidates, remaining[0], trail)

        self._load_appearances(remaining)
        source_book = _book_of(ctx.source_key)

        # 3. Tanach only: the candidate(s) known to appear in this book.
        if ctx.source_type == SourceType.TN:
            remaining = self._keep_best(remaining, f"known to appear in {source_book[1]}",
                                        lambda c: (int(source_book in c.known_books),), trail)
            if len(remaining) == 1:
                return self._decided(entity, ctx, candidates, remaining[0], trail)

        # 4. Fallback: the most prominent; ties go to the earliest created (keys are ObjectIds).
        scores = {c.key: self._prominence(ctx, c) for c in remaining}
        trail.append("fallback - prominence (known in book, mentions in book, known in source type, "
                     f"mentions in source type, mentions, relationships): {scores}")
        chosen = max(sorted(remaining, key=lambda c: c.key), key=lambda c: scores[c.key])
        return self._decided(entity, ctx, candidates, chosen, trail)

    # ─── Contradictions ───────────────────────────────────────────────────────

    @staticmethod
    def _contradiction(ctx: PersonSourceContext, candidate: _Candidate) -> Optional[str]:
        """Why this source cannot be talking about this candidate, or None if it might be."""
        if ctx.source_type == SourceType.TN and candidate.is_talmudic_sage():
            return "a Tanna/Amora cannot appear in a Tanach source"
        for label, passage_parents, signature in (("father", ctx.fathers, _FATHER_SIGNATURE),
                                                  ("mother", ctx.mothers, _MOTHER_SIGNATURE)):
            known_parents = candidate.related_by_signature.get(signature, [])
            if passage_parents and known_parents and not any(
                    parent.matches(name) for name in passage_parents for parent in known_parents):
                return f"{label} {sorted(passage_parents)} vs known {sorted(p.display_name for p in known_parents)}"
        return None

    # ─── Scores ───────────────────────────────────────────────────────────────

    @staticmethod
    def _common_relationships_score(ctx: PersonSourceContext, candidate: _Candidate) -> Tuple[int, int, int]:
        """(# of the mention's relationships the candidate also has, # of those with a Person, # with a Place)."""
        total = with_person = with_place = 0
        for rel in ctx.relations:
            known = candidate.related_by_signature.get(_rel_signature(rel.rel_type, rel.person_is_term1), [])
            matched_types = {other.entity_type for other in known if other.matches(rel.other_name)}
            if not matched_types:
                continue
            total += 1
            if EntityType.EPerson in matched_types:
                with_person += 1
            elif EntityType.EPlace in matched_types:
                with_place += 1
        return total, with_person, with_place

    @staticmethod
    def _related_entities_in_source(ctx: PersonSourceContext, candidate: _Candidate) -> int:
        """How many of the other entities this source mentions the candidate is related to."""
        return sum(1 for name in ctx.source_entity_names if candidate.is_related_to(name))

    @staticmethod
    def _prominence(ctx: PersonSourceContext, candidate: _Candidate) -> Tuple[int, int, int, int, int, int]:
        """
        (known to appear in this book, mentions in this book, known to appear in this source type,
         mentions in this source type, mentions overall, relationships).
        """
        source_book = _book_of(ctx.source_key)
        source_type = source_book[0]
        mentioned_books = [_book_of(k) for k in candidate.source_keys]
        return (
            int(source_book in candidate.known_books),
            mentioned_books.count(source_book),
            int(any(book_type == source_type for book_type, _ in candidate.known_books)),
            sum(1 for book_type, _ in mentioned_books if book_type == source_type),
            len(mentioned_books),
            candidate.relationship_count,
        )

    @staticmethod
    def _keep_best(candidates: List[_Candidate], step_name: str, score: Callable[[_Candidate], tuple],
                   trail: List[str]) -> List[_Candidate]:
        """
        Keeps only the best-scoring candidates - or all of them if nobody scored above zero
        (the step gave no evidence). Steps that gave evidence are recorded in `trail`.
        """
        scores = {c.key: score(c) for c in candidates}
        best = max(scores.values())
        if not any(best):
            return candidates
        trail.append(f"{step_name}: {scores}")
        return [c for c in candidates if scores[c.key] == best]

    # ─── DB loading ───────────────────────────────────────────────────────────

    def _load_candidates(self, entities: List[Entity], with_relations: bool) -> List[_Candidate]:
        candidates = [_Candidate(entity=e) for e in entities]
        if not with_relations:
            return candidates

        by_key = {c.key: c for c in candidates}
        rels = self.db_api.get_rels_for_entities(list(by_key))
        others = self._get_entity_infos(
            {r.term2 for r in rels if r.term1 in by_key} | {r.term1 for r in rels if r.term2 in by_key})

        for rel in rels:
            if rel.term1 == rel.term2:
                continue
            for candidate_key, other_key, candidate_is_term1 in ((rel.term1, rel.term2, True),
                                                                 (rel.term2, rel.term1, False)):
                if candidate_key in by_key and other_key in others:
                    by_key[candidate_key].add_relation(_rel_signature(rel.rel_type, candidate_is_term1),
                                                       others[other_key])
        return candidates

    def _get_entity_infos(self, keys: Set[str]) -> Dict[str, _EntityInfo]:
        missing = [k for k in keys if k not in self._entity_info_cache]
        if missing:
            found = {e.key: _EntityInfo.from_entity(e) for e in self.db_api.get_entities_by_keys(missing)}
            for k in missing:
                self._entity_info_cache[k] = found.get(k)
        return {k: self._entity_info_cache[k] for k in keys if self._entity_info_cache[k] is not None}

    def _load_appearances(self, candidates: List[_Candidate]) -> None:
        """Loads, for each candidate, the sources mentioning it and the books it is known to appear in."""
        pending = {c.key: c for c in candidates if c.source_keys is None}
        if not pending:
            return
        for c in pending.values():
            c.source_keys = set()
        for src_metadata in self.db_api.get_source_metadata_filtered(entity_ids=list(pending)):
            for key in pending.keys() & src_metadata.entity_keys:
                pending[key].source_keys.add(src_metadata.key)
        for c in pending.values():
            c.known_books = _referenced_books(c.entity) | {_book_of(k) for k in c.source_keys}

    # ─── Logging ──────────────────────────────────────────────────────────────

    def _decided(self, entity: Entity, ctx: PersonSourceContext, candidates: List[_Candidate],
                 chosen: _Candidate, trail: List[str]) -> str:
        self._log(entity, ctx, f"{len(candidates)} candidates -> {chosen.key} | " + " | ".join(trail))
        return chosen.key

    @staticmethod
    def _log(entity: Entity, ctx: PersonSourceContext, message: str) -> None:
        print(f"{_LOG_PREFIX} '{entity.display_en_name}' in {ctx.source_key}: {message}")
