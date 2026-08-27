# bs"d
"""
EntityIgnoreFilter - filters out non-proper-noun Person/Place entities returned by the LLM.

Sometimes the LLM extracts generic nouns instead of proper nouns (e.g. "the advisor",
"the wilderness"). This module discards:
  - Person entities whose name CONTAINS (as a substring, case-insensitively) one of the
    generic terms listed in entities_to_ignore/Person.
  - Place entities whose name EXACTLY MATCHES (case-insensitively) one of the generic
    terms listed in entities_to_ignore/Place. Place names that merely contain such a term
    (e.g. "Wilderness of Sin") are kept, since they are still proper nouns.

Person matching uses an Aho-Corasick automaton, built once and cached, so checking a name
against the full ignore list (hundreds of terms) costs O(len(name)) instead of
O(len(name) * num_terms) as a naive per-term substring loop would. Place matching uses a
simple cached set lookup since it only needs exact-match comparisons.
"""

import os
from collections import deque
from typing import Dict, Iterable, List, Optional, Set

from backend.common import Paths
from backend.models_db.Enums import EntityType

# Maps EntityType -> ignore-list filename under Paths.ENTITIES_TO_IGNORE_DIR/.
# Only entity types listed here are subject to filtering.
_ENTITY_TYPE_TO_IGNORE_FILE: Dict[EntityType, str] = {
    EntityType.EPerson: "Person",
    EntityType.EPlace: "Place",
}

# Entity types filtered via substring (CONTAINS) matching, using the Aho-Corasick automaton.
_SUBSTRING_MATCH_TYPES = {EntityType.EPerson}

# Entity types filtered via exact-match comparison only.
_EXACT_MATCH_TYPES = {EntityType.EPlace}


class _AhoCorasick:
    """Minimal Aho-Corasick automaton for fast multi-pattern substring containment checks."""

    def __init__(self, patterns: Iterable[str]):
        self._goto: List[Dict[str, int]] = [{}]
        self._fail: List[int] = [0]
        self._is_end: List[bool] = [False]

        for pattern in patterns:
            self._add_pattern(pattern)
        self._build_fail_links()

    def _add_pattern(self, pattern: str) -> None:
        node = 0
        for ch in pattern:
            nxt = self._goto[node].get(ch)
            if nxt is None:
                self._goto.append({})
                self._fail.append(0)
                self._is_end.append(False)
                nxt = len(self._goto) - 1
                self._goto[node][ch] = nxt
            node = nxt
        self._is_end[node] = True

    def _build_fail_links(self) -> None:
        """Standard BFS construction of failure links (Aho-Corasick, 1975)."""
        queue = deque()
        for nxt in self._goto[0].values():
            self._fail[nxt] = 0
            queue.append(nxt)

        while queue:
            node = queue.popleft()
            for ch, nxt in self._goto[node].items():
                queue.append(nxt)
                f = self._fail[node]
                while f != 0 and ch not in self._goto[f]:
                    f = self._fail[f]
                candidate = self._goto[f].get(ch, 0)
                self._fail[nxt] = candidate if candidate != nxt else 0
                self._is_end[nxt] = self._is_end[nxt] or self._is_end[self._fail[nxt]]

    def contains_any(self, text: str) -> bool:
        """Return True as soon as any pattern is found as a substring of *text*."""
        node = 0
        for ch in text:
            while node != 0 and ch not in self._goto[node]:
                node = self._fail[node]
            node = self._goto[node].get(ch, 0)
            if self._is_end[node]:
                return True
        return False


# Lazily built + cached per entity type so the ignore files are read and the
# automaton/set is constructed only once per process, regardless of how many
# entities are checked.
_automaton_cache: Dict[EntityType, Optional[_AhoCorasick]] = {}
_exact_terms_cache: Dict[EntityType, Set[str]] = {}


def _load_ignore_terms(entity_type: EntityType) -> List[str]:
    filename = _ENTITY_TYPE_TO_IGNORE_FILE[entity_type]
    path = os.path.join(Paths.ENTITIES_TO_IGNORE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]


def _get_automaton(entity_type: EntityType) -> Optional[_AhoCorasick]:
    if entity_type not in _automaton_cache:
        if entity_type in _ENTITY_TYPE_TO_IGNORE_FILE:
            terms = _load_ignore_terms(entity_type)
            _automaton_cache[entity_type] = _AhoCorasick(terms) if terms else None
        else:
            _automaton_cache[entity_type] = None
    return _automaton_cache[entity_type]


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

    - Person: discarded if *name* CONTAINS (as a substring, case-insensitively) one
      of the configured terms.
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
        automaton = _get_automaton(entity_type)
        if automaton is None:
            return False
        return automaton.contains_any(name.lower())

    return False


__all__ = ["is_ignored_entity_name"]
