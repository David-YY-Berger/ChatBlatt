# bs"d - lehagdil torah velahadir
"""
Reciprocal Rank Fusion (RRF): a simple, scale-free way to combine several
independently-ranked lists of the same keys into one merged ranking.

Used to combine FAISS's semantic-embedding similarity ranking with BM25's
lexical/keyword similarity ranking (see backend.faiss_api.FaissEngine and
backend.bm25_api.BM25Engine) into a single text-similarity ordering, without
having to reconcile the very different score scales/distributions the two
methods produce (FAISS: L2 distance; BM25: unbounded term-frequency-based
score) - RRF only looks at each key's *rank* (position) in each list.

Reference: Cormack, Clarke & Buettcher, "Reciprocal Rank Fusion Outperforms
Condorcet and Individual Rank Learning Methods", SIGIR 2009.
"""

from typing import Dict, Iterable, List, TypeVar

T = TypeVar("T")

# Standard damping constant from the original RRF paper. Larger values flatten
# the influence of top-ranked items (making the fusion less sensitive to any
# single list's #1 pick); smaller values weight top ranks more heavily.
DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(rankings: Iterable[List[T]], k: int = DEFAULT_RRF_K) -> List[T]:
    """
    Fuse multiple best-first ranked lists into a single best-first ranking
    using Reciprocal Rank Fusion.

    Every key that appears in *any* input list contributes:
        score(key) += 1 / (k + rank_in_that_list + 1)
    (rank_in_that_list is 0-based, so the top item scores 1/(k+1)). A key
    missing from a given list simply contributes 0 for that list - it is
    *not* penalized beyond not getting that list's contribution, so a key
    ranked #1 by one engine and altogether unranked by the other still
    surfaces near the top of the fused ranking.

    Keys are then sorted by descending combined score (ties keep the order
    they were first encountered, for determinism).

    This function never drops or filters any key: the returned list is
    exactly the union of every key appearing in `rankings`, each exactly
    once. Callers that also have keys absent from *every* input ranking
    should append those themselves (see SourceSearchHandler), so nothing a
    caller cares about ever disappears purely because neither engine ranked
    it.

    :param rankings: An iterable of ranked-key lists, e.g.
                      [faiss_ranked_keys, bm25_ranked_keys]. Empty lists are
                      fine (e.g. an index with 0 vectors/documents yet).
    :param k:         RRF damping constant (60 = standard default).
    :return:          Fused list of keys, best-first.
    """
    scores: Dict[T, float] = {}
    first_seen_order: List[T] = []

    for ranking in rankings:
        for rank, key in enumerate(ranking):
            if key not in scores:
                scores[key] = 0.0
                first_seen_order.append(key)
            scores[key] += 1.0 / (k + rank + 1)

    return sorted(first_seen_order, key=lambda key: scores[key], reverse=True)
