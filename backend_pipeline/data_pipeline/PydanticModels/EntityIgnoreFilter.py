# bs"d
"""
EntityIgnoreFilter - filters out non-proper-noun Person/Place entities returned by the LLM.

Sometimes the LLM extracts generic nouns instead of proper nouns (e.g. "the advisor",
"the wilderness"). This module discards any Person/Place entity whose name CONTAINS
(as a substring, not only a full match, case-insensitively) one of the generic terms
listed in entities_to_ignore/Person and entities_to_ignore/Place.

Matching uses an Aho-Corasick automaton, built once per entity type and cached, so
checking a name against the full ignore list (hundreds of terms) costs O(len(name))
instead of O(len(name) * num_terms) as a naive per-term substring loop would.
"""

import os
from collections import deque
from typing import Dict, Iterable, List, Optional

from backend.models_db.Enums import EntityType

_IGNORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entities_to_ignore")

# Maps EntityType -> ignore-list filename under entities_to_ignore/.
# Only entity types listed here are subject to filtering.
_ENTITY_TYPE_TO_IGNORE_FILE: Dict[EntityType, str] = {
    EntityType.EPerson: "Person",
    EntityType.EPlace: "Place",
}


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
# automaton is constructed only once per process, regardless of how many
# entities are checked.
_automaton_cache: Dict[EntityType, Optional[_AhoCorasick]] = {}


def _load_ignore_terms(entity_type: EntityType) -> List[str]:
    filename = _ENTITY_TYPE_TO_IGNORE_FILE[entity_type]
    path = os.path.join(_IGNORE_DIR, filename)
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


def is_ignored_entity_name(name: str, entity_type: EntityType) -> bool:
    """
    Return True if *name* should be discarded because it contains (as a substring,
    case-insensitively) one of the generic, non-proper-noun terms configured for
    *entity_type* under entities_to_ignore/. Entity types without an ignore list
    (i.e. anything other than Person/Place) always return False.
    """
    if not name:
        return False
    automaton = _get_automaton(entity_type)
    if automaton is None:
        return False
    return automaton.contains_any(name.lower())


__all__ = ["is_ignored_entity_name"]
