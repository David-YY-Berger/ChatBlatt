# bs"d
"""
EntityIgnoreFilter - filters out non-proper-noun Person/Place entities returned by the LLM.

Sometimes the LLM extracts generic nouns instead of proper nouns (e.g. "the advisor",
"the wilderness"). This module discards:
  - Person entities whose name CONTAINS, as a whole word/token (case-insensitively, word-
    boundary delimited - NOT a raw substring), one of the generic terms listed in
    entities_to_ignore/Person. Word-boundary matching is essential: a raw substring check
    would wrongly flag proper nouns that merely happen to contain an ignore term as part of
    a longer word - e.g. "Manasseh" contains "man", "Amalek" contains "male", "Haman"/
    "Naaman" contain "man" - none of which are the generic word itself. "King Ahaz" still
    correctly matches "king" as its own word and gets filtered (see NAME_FIELDS note in
    DBPrePopulateAmbiguosEntitys / the entity_prepopulation_guide for the companion fix:
    the extraction prompt should not emit titles like "King" in en_name to begin with).
  - Place entities whose name EXACTLY MATCHES (case-insensitively) one of the generic
    terms listed in entities_to_ignore/Place. Place names that merely contain such a term
    (e.g. "Wilderness of Sin") are kept, since they are still proper nouns.

Person matching uses one compiled regex (word-boundary alternation over all ignore terms),
built once and cached, so checking a name against the full ignore list (hundreds of terms)
is a single regex search rather than a per-term loop. Place matching uses a simple cached
set lookup since it only needs exact-match comparisons.
"""

import os
import re
from typing import Dict, Iterable, List, Optional, Pattern, Set

from backend.common import Paths
from backend.models_db.Enums import EntityType

# Maps EntityType -> ignore-list filename under Paths.ENTITIES_TO_IGNORE_DIR/.
# Only entity types listed here are subject to filtering.
_ENTITY_TYPE_TO_IGNORE_FILE: Dict[EntityType, str] = {
    EntityType.EPerson: "Person",
    EntityType.EPlace: "Place",
}

# Entity types filtered via whole-word (CONTAINS AS A WORD) matching.
_SUBSTRING_MATCH_TYPES = {EntityType.EPerson}

# Entity types filtered via exact-match comparison only.
_EXACT_MATCH_TYPES = {EntityType.EPlace}


def _compile_word_boundary_pattern(terms: Iterable[str]) -> Optional[Pattern]:
    """
    Builds one compiled regex matching any of *terms* as a whole word (\\b-delimited),
    case-insensitively. Terms are expected to already be lowercase. Returns None if
    *terms* is empty. \\b works correctly even for hyphenated terms (e.g. "father-in-law")
    since the boundary assertions only apply at the very start/end of each alternative.
    """
    escaped = [re.escape(t) for t in terms]
    if not escaped:
        return None
    # Longest-first is not required for correctness (this is a pure "any match" check,
    # not an extraction), but keeps the generated pattern easier to read when inspected.
    escaped.sort(key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b")


# Lazily built + cached per entity type so the ignore files are read and the
# regex/set is constructed only once per process, regardless of how many
# entities are checked.
_word_boundary_pattern_cache: Dict[EntityType, Optional[Pattern]] = {}
_exact_terms_cache: Dict[EntityType, Set[str]] = {}


def _load_ignore_terms(entity_type: EntityType) -> List[str]:
    filename = _ENTITY_TYPE_TO_IGNORE_FILE[entity_type]
    path = os.path.join(Paths.ENTITIES_TO_IGNORE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]


def _get_word_boundary_pattern(entity_type: EntityType) -> Optional[Pattern]:
    if entity_type not in _word_boundary_pattern_cache:
        if entity_type in _ENTITY_TYPE_TO_IGNORE_FILE:
            terms = _load_ignore_terms(entity_type)
            _word_boundary_pattern_cache[entity_type] = _compile_word_boundary_pattern(terms)
        else:
            _word_boundary_pattern_cache[entity_type] = None
    return _word_boundary_pattern_cache[entity_type]


def _get_exact_terms(entity_type: EntityType) -> Set[str]:
    if entity_type not in _exact_terms_cache:
        if entity_type in _ENTITY_TYPE_TO_IGNORE_FILE:
            _exact_terms_cache[entity_type] = set(_load_ignore_terms(entity_type))
        else:
            _exact_terms_cache[entity_type] = set()
    return _exact_terms_cache[entity_type]


def is_ignored_entity_name(name: str, entity_type: EntityType) -> bool:
    """
    Return True if *name* should be discarded as a generic, non-proper-noun term
    configured for *entity_type* under Paths.ENTITIES_TO_IGNORE_DIR/.

    - Person: discarded if *name* CONTAINS one of the configured terms AS A WHOLE WORD
      (case-insensitively, word-boundary delimited). E.g. "King Ahaz" is discarded (it
      contains the standalone word "king"), but "Manasseh", "Amalek", "Haman", "Naaman"
      are NOT (the ignore terms "man"/"male" only appear there as part of a longer word).
    - Place: discarded only if *name* EXACTLY MATCHES (case-insensitively) one of the
      configured terms. A place name that merely contains a term (e.g. "Wilderness of
      Sin") is kept, since it is still a proper noun.

    Entity types without an ignore list (i.e. anything other than Person/Place) always
    return False.
    """
    if not name:
        return False

    if entity_type in _EXACT_MATCH_TYPES:
        return name.lower() in _get_exact_terms(entity_type)

    if entity_type in _SUBSTRING_MATCH_TYPES:
        pattern = _get_word_boundary_pattern(entity_type)
        if pattern is None:
            return False
        return pattern.search(name.lower()) is not None

    return False


__all__ = ["is_ignored_entity_name"]
