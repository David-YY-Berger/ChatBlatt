# bs"d
"""
merge_candidates - pure (DB-free) logic for finding and rendering *candidate* entity merges
for human review. See control_docs/pipeline/merge_candidates.md.

Nothing here touches the DB: callers pass in entities / rels / a key->entity name map, so the
logic is unit-testable (test_merge_candidates.py). Nothing here merges anything either - the
output is review files whose decisions are applied by a separate (future) step.

Candidate kinds (one review-file family each):
  - "prefix":    same name once a title prefix (rabbi / rav / abba / ...) is stripped, with at
                 least two distinct display names ("akiva" / "rabbi akiva" / "rav akiva").
  - "same_name": identical display_en_name (case-insensitive) on 2+ entities.
  - "close_spelling" (hanna / hana / hannah): TBD, not implemented.

Review file format (markdown, readable by humans AND machines):
  every group is introduced by one machine-readable HTML comment
      <!-- merge-group: {"id": "...", "kind": "...", "keys": ["<entity key>", ...]} -->
  followed by two checkboxes. The human ticks (replaces the space with x) at most one:
      - [ ] merge          -> merge every entity in `keys` into one
      - [ ] dont merge     -> keep them separate
  Neither ticked = undecided (do nothing); both ticked = conflict (do nothing).
"""

import html
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

KIND_PREFIX = "prefix"
KIND_SAME_NAME = "same_name"

# Longest alternatives first is unnecessary (whole-word match), listed for readability.
TITLE_PREFIXES = ("rabbi", "rabban", "rebbi", "rav", "abba", "reb", "r.")
_PREFIX_RE = re.compile(r"^(?:%s)\s+(?P<base>\S.*)$" % "|".join(re.escape(p) for p in TITLE_PREFIXES))

GOD_NAMES = {"god", "hashem", "god hashem", "god most high", "the lord", "lord"}
# Rels where term1 is a descendant of term2 - a God term2 here is almost certainly a bug.
PARENT_REL_TYPES = {"childOfFather", "childOfMother", "descendantOf"}

DEFAULT_MAX_ENTITIES_PER_FILE = 100
MAX_RELS_SHOWN_PER_ENTITY = 40

MERGE_CHECKBOX = "- [ ] merge"
DONT_MERGE_CHECKBOX = "- [ ] dont merge"
_GROUP_COMMENT_RE = re.compile(r"<!-- merge-group: (\{.*\}) -->")
_MERGE_TICKED_RE = re.compile(r"^- \[[xX]\] merge\s*$")
_DONT_MERGE_TICKED_RE = re.compile(r"^- \[[xX]\] dont merge\s*$")


@dataclass
class Group:
    id: str
    kind: str
    label: str
    entities: List[Any]  # Entity objects (duck-typed: key, display_en_name, ...)


# ─── Name helpers ───────────────────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    return " ".join((name or "").lower().split())


def split_title_prefix(name: str) -> Tuple[Optional[str], str]:
    """'rabbi akiva' -> ('rabbi', 'akiva'); 'akiva' -> (None, 'akiva'). Name is normalized first."""
    norm = normalize_name(name)
    m = _PREFIX_RE.match(norm)
    if not m:
        return None, norm
    return norm[: norm.index(" ")], m.group("base")


def is_god_name(name: str) -> bool:
    norm = normalize_name(name)
    if not norm:
        return False
    return norm in GOD_NAMES or norm.split(" ")[0] in {"god", "hashem"}


# ─── Candidate finding ──────────────────────────────────────────────────────────

def build_indexes(entities: Iterable[Any]) -> Tuple[Dict[str, List[Any]], Dict[str, List[Any]]]:
    """Returns (by_exact_name, by_base_name), both keyed by normalized name."""
    by_name: Dict[str, List[Any]] = {}
    by_base: Dict[str, List[Any]] = {}
    for e in entities:
        name = normalize_name(e.display_en_name)
        if not name:
            continue
        by_name.setdefault(name, []).append(e)
        by_base.setdefault(split_title_prefix(name)[1], []).append(e)
    return by_name, by_base


def prefix_group_for(entity: Any, by_base: Dict[str, List[Any]]) -> Optional[Group]:
    """The title-prefix group `entity` belongs to, or None (needs 2+ distinct display names)."""
    base = split_title_prefix(entity.display_en_name)[1]
    members = by_base.get(base, [])
    if len({normalize_name(m.display_en_name) for m in members}) < 2:
        return None
    return Group(id=f"{KIND_PREFIX}:{base}", kind=KIND_PREFIX, label=base, entities=sorted_members(members))


def same_name_group_for(entity: Any, by_name: Dict[str, List[Any]]) -> Optional[Group]:
    name = normalize_name(entity.display_en_name)
    members = by_name.get(name, [])
    if len(members) < 2:
        return None
    return Group(id=f"{KIND_SAME_NAME}:{name}", kind=KIND_SAME_NAME, label=name, entities=sorted_members(members))


def sorted_members(members: List[Any]) -> List[Any]:
    return sorted(members, key=lambda e: (normalize_name(e.display_en_name), e.key))


def find_groups(entities: List[Any], kind: str, max_entities_to_check: Optional[int]) -> Tuple[List[Group], int]:
    """
    Iterate entities (sorted by name) and collect candidate groups of `kind`. Indexes are built
    over ALL entities (so a group is always complete), but only the first `max_entities_to_check`
    entities (None = all) are *checked* as starting points. Entities with no candidates are skipped.
    Returns (groups, number_of_entities_checked).
    """
    by_name, by_base = build_indexes(entities)
    ordered = sorted(entities, key=lambda e: (normalize_name(e.display_en_name), e.key))
    if max_entities_to_check is not None:
        ordered = ordered[:max_entities_to_check]

    groups: Dict[str, Group] = {}
    for e in ordered:
        if kind == KIND_PREFIX:
            group = prefix_group_for(e, by_base)
        elif kind == KIND_SAME_NAME:
            group = same_name_group_for(e, by_name)
        else:
            raise ValueError(f"Unsupported candidate kind: {kind}")
        if group is not None and group.id not in groups:
            groups[group.id] = group
    return list(groups.values()), len(ordered)


def chunk_groups(groups: List[Group], max_entities_per_file: int = DEFAULT_MAX_ENTITIES_PER_FILE) -> List[List[Group]]:
    """Split groups into files of at most `max_entities_per_file` entities (a group is never split)."""
    chunks: List[List[Group]] = []
    current: List[Group] = []
    count = 0
    for g in groups:
        if current and count + len(g.entities) > max_entities_per_file:
            chunks.append(current)
            current, count = [], 0
        current.append(g)
        count += len(g.entities)
    if current:
        chunks.append(current)
    return chunks


# ─── Rendering ──────────────────────────────────────────────────────────────────

def describe_rels(entity_key: str, rels: List[Any], names: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    One markdown line per rel touching `entity_key`, plus warnings.
    `names` maps entity key -> Entity (for the other side). Outgoing: `type -> other`;
    incoming: `other -> type`. Warns when this entity is the child/descendant of a God/Hashem entity.
    """
    lines: List[str] = []
    warnings: List[str] = []
    for rel in sorted(rels, key=lambda r: (r.rel_type.value, r.term1, r.term2)):
        outgoing = rel.term1 == entity_key
        other_key = rel.term2 if outgoing else rel.term1
        other = names.get(other_key)
        other_name = other.display_en_name if other is not None else "?"
        other_type = other.entityType.value if other is not None else "?"
        ref = f"`{other_name}` ({other_type}, `{other_key}`)"
        lines.append(f"{rel.rel_type.value} -> {ref}" if outgoing else f"{ref} -> {rel.rel_type.value}")
        if outgoing and rel.rel_type.value in PARENT_REL_TYPES and other is not None and is_god_name(other_name):
            warnings.append(f"GOD/HASHEM AS PARENT: {rel.rel_type.value} -> `{other_name}` (should not happen)")
    return lines, warnings


def render_entity(index: int, entity: Any, rels: List[Any], names: Dict[str, Any]) -> str:
    rel_lines, warnings = describe_rels(entity.key, rels, names)
    out = [f"#### Entity {index}: `{entity.display_en_name}` (key: `{entity.key}`)"]
    out.append(f"- Hebrew name: {getattr(entity, 'display_heb_name', '') or '-'}")
    other_names = [n for n in (entity.all_en_names or []) if normalize_name(n) != normalize_name(entity.display_en_name)]
    out.append(f"- Other names: {', '.join(other_names) or '-'}")
    out.append(
        f"- Time period: {_enum_value(getattr(entity, 'timePeriod', None))} | "
        f"isWoman: {getattr(entity, 'isWoman', None)} | isNonJew: {getattr(entity, 'isNonJew', None)} | "
        f"isGroup: {getattr(entity, 'isGroup', None)}"
    )
    roles = [_enum_value(r) for r in (getattr(entity, "roles", None) or [])]
    out.append(f"- Roles: {', '.join(roles) or '-'}")
    if entity.book_references:
        out.append(f"- Pre-populated (book_references: {', '.join(entity.book_references)}) - may be a DELIBERATELY separate person")
    for w in warnings:
        out.append(f"- WARNING {w}")
    out.append(f"- Relationships ({len(rel_lines)}):")
    for line in rel_lines[:MAX_RELS_SHOWN_PER_ENTITY]:
        out.append(f"  - {line}")
    if len(rel_lines) > MAX_RELS_SHOWN_PER_ENTITY:
        out.append(f"  - ... {len(rel_lines) - MAX_RELS_SHOWN_PER_ENTITY} more")
    return "\n".join(out)


def _enum_value(v: Any) -> Any:
    return getattr(v, "value", v)


def render_group(group: Group, rels_by_entity: Dict[str, List[Any]], names: Dict[str, Any], number: int,
                 decision: str = "undecided") -> str:
    meta = json.dumps({"id": group.id, "kind": group.kind, "keys": [e.key for e in group.entities]}, ensure_ascii=False)
    status = {"merge": "merge", "dont_merge": "dont merge"}.get(decision, "undecided")
    label = html.escape(group.label)
    parts = [f"<details>", f"<summary><b>Group {number}: \"{label}\" ({len(group.entities)} entities)</b> - {status}</summary>",
             "", f"<!-- merge-group: {meta} -->"]
    if group.kind == KIND_PREFIX:
        parts.append(f"Suggested final display name: `{group.label}`")
    parts.append("")
    parts.append(MERGE_CHECKBOX.replace("[ ]", "[x]") if decision == "merge" else MERGE_CHECKBOX)
    parts.append(DONT_MERGE_CHECKBOX.replace("[ ]", "[x]") if decision == "dont_merge" else DONT_MERGE_CHECKBOX)
    parts.append("")
    for i, e in enumerate(group.entities, 1):
        parts.append(render_entity(i, e, rels_by_entity.get(e.key, []), names))
        parts.append("")
    parts.append("</details>")
    parts.append("")
    parts.append("---")
    return "\n".join(parts)


FILE_HEADER = """# Merge candidates: {title} - file {file_no}/{file_count}

{description}

**How to review:** under each group tick `[x]` on exactly ONE line:
- `- [x] merge` - these entities are the same; merge them into one.
- `- [x] dont merge` - they are different; keep them separate.
Leave both unticked to decide later (undecided groups are ignored). Tip: to merge most groups,
just tick `dont merge` on the few exceptions (and vice versa) - a later step can apply a default
to the unticked rest. Do not edit the `<!-- merge-group: ... -->` comments (machine-readable).

Groups in this file: {group_count}
"""


def render_file(title: str, description: str, groups: List[Group], rels_by_entity: Dict[str, List[Any]],
                names: Dict[str, Any], file_no: int, file_count: int, first_group_number: int,
                decisions: Optional[Dict[str, str]] = None) -> str:
    decisions = decisions or {}
    header = FILE_HEADER.format(title=title, description=description, file_no=file_no,
                                file_count=file_count, group_count=len(groups))
    body = "\n\n".join(
        render_group(g, rels_by_entity, names, first_group_number + i, decisions.get(g.id, "undecided")) for i, g in enumerate(groups)
    )
    return f"{header}\n---\n\n{body}\n"


# ─── Confidence ratings (separate control file, sorted most confident first) ────

_CONFIDENCE_COMMENT_RE = re.compile(r"<!-- merge-confidence: (\{.*\}) -->")
_FATHER_MOTHER_RELS = {"childOfFather", "childOfMother"}
BASE_CONFIDENCE = {KIND_PREFIX: 85, KIND_SAME_NAME: 40}


def _known_and_differ(a: Any, b: Any) -> bool:
    return a is not None and b is not None and a != b


def _parents(entity_key: str, rels: List[Any]) -> set:
    return {r.term2 for r in rels if r.term1 == entity_key and r.rel_type.value in _FATHER_MOTHER_RELS}


def _related_keys(entity_key: str, rels: List[Any]) -> set:
    return {r.term2 if r.term1 == entity_key else r.term1 for r in rels}


def _pair_confidence(kind: str, a: Any, b: Any, rels_a: List[Any], rels_b: List[Any]) -> Tuple[int, List[str]]:
    score = BASE_CONFIDENCE.get(kind, 40)
    reasons: List[str] = [f"base {score}% ({'title-prefix' if kind == KIND_PREFIX else 'same name'})"]

    def adjust(delta: int, reason: str) -> None:
        nonlocal score
        score += delta
        reasons.append(f"{delta:+d}: {reason}")

    for attr, delta, label in (("isWoman", -40, "gender differs"), ("isNonJew", -30, "isNonJew differs"),
                               ("isGroup", -30, "isGroup differs")):
        if _known_and_differ(getattr(a, attr, None), getattr(b, attr, None)):
            adjust(delta, label)
    if _known_and_differ(_enum_value(getattr(a, "timePeriod", None)), _enum_value(getattr(b, "timePeriod", None))):
        adjust(-20, "time period differs")
    heb_a, heb_b = (getattr(a, "display_heb_name", "") or "").strip(), (getattr(b, "display_heb_name", "") or "").strip()
    if heb_a and heb_b:
        adjust(5, "same Hebrew name") if heb_a == heb_b else adjust(-15, "Hebrew names differ")
    if a.book_references and b.book_references and not set(a.book_references) & set(b.book_references):
        adjust(-20, "pre-populated in different books")
    elif a.book_references or b.book_references:
        adjust(-5, "pre-populated (possibly deliberately separate)")
    parents_a, parents_b = _parents(a.key, rels_a), _parents(b.key, rels_b)
    if parents_a and parents_b:
        adjust(10, "shared parent") if parents_a & parents_b else adjust(-25, "different parents")
    shared = (_related_keys(a.key, rels_a) & _related_keys(b.key, rels_b)) - {a.key, b.key}
    if shared:
        adjust(min(10, 3 * len(shared)), f"{len(shared)} shared related entit{'y' if len(shared) == 1 else 'ies'}")
    return max(0, min(100, score)), reasons


def rate_group(group: Group, rels_by_entity: Dict[str, List[Any]]) -> Tuple[int, List[str]]:
    """Confidence (0-100) that all entities of `group` are the same person = the weakest pair's score."""
    worst: Optional[Tuple[int, List[str]]] = None
    ents = group.entities
    for i in range(len(ents)):
        for j in range(i + 1, len(ents)):
            a, b = ents[i], ents[j]
            result = _pair_confidence(group.kind, a, b, rels_by_entity.get(a.key, []), rels_by_entity.get(b.key, []))
            if worst is None or result[0] < worst[0]:
                worst = (result[0], [f"weakest pair: `{a.display_en_name}` vs `{b.display_en_name}`"] + result[1])
    return worst if worst is not None else (0, ["fewer than 2 entities"])


def rate_groups(groups: List[Group], rels_by_entity: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """[{id, kind, label, keys, confidence, reasons}] sorted most confident first (ties by id)."""
    rated = []
    for g in groups:
        confidence, reasons = rate_group(g, rels_by_entity)
        rated.append({"id": g.id, "kind": g.kind, "label": g.label, "keys": [e.key for e in g.entities],
                      "confidence": confidence, "reasons": reasons})
    return sorted(rated, key=lambda r: (-r["confidence"], r["id"]))


CONFIDENCE_HEADER = """# Merge confidence: {title}

Confidence (0-100%) that all entities of each group are the same person, most confident first.
Machine-read control file - do not edit the `<!-- merge-confidence: ... -->` comments.
Advisory only: decisions are still made by ticking the review files.

Groups: {count}
"""


def render_confidence_file(title: str, rated: List[Dict[str, Any]]) -> str:
    parts = [CONFIDENCE_HEADER.format(title=title, count=len(rated))]
    for rank, r in enumerate(rated, 1):
        meta = json.dumps({"id": r["id"], "confidence": r["confidence"], "keys": r["keys"]}, ensure_ascii=False)
        parts.append(f"{rank}. **{r['confidence']}%** \"{html.escape(r['label'])}\" ({len(r['keys'])} entities) "
                     f"<!-- merge-confidence: {meta} -->")
        parts.extend(f"   - {reason}" for reason in r["reasons"])
        parts.append("")
    return "\n".join(parts)


def parse_confidence_file(text: str) -> List[Dict[str, Any]]:
    """[{"id", "confidence", "keys"}] in file order (most confident first)."""
    return [json.loads(m.group(1)) for line in text.splitlines() if (m := _CONFIDENCE_COMMENT_RE.search(line))]


# ─── Reading decisions back (machine side) ──────────────────────────────────────

def parse_review_file(text: str) -> List[Dict[str, Any]]:
    """
    Parse a review file into [{"id", "kind", "keys", "decision"}], decision being one of
    "merge", "dont_merge", "undecided" (neither ticked) or "conflict" (both ticked).
    """
    results: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    merge = dont = False

    def flush():
        if current is not None:
            if merge and dont:
                current["decision"] = "conflict"
            else:
                current["decision"] = "merge" if merge else "dont_merge" if dont else "undecided"
            results.append(current)

    for line in text.splitlines():
        m = _GROUP_COMMENT_RE.search(line)
        if m:
            flush()
            current, merge, dont = json.loads(m.group(1)), False, False
        elif current is not None:
            merge = merge or bool(_MERGE_TICKED_RE.match(line.strip()))
            dont = dont or bool(_DONT_MERGE_TICKED_RE.match(line.strip()))
    flush()
    return results


# ─── Carrying decisions across re-runs ──────────────────────────────────────────

def carry_over_decisions(groups: List[Group], previous: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Decisions (only "merge"/"dont_merge") from a previous review-file generation that are still
    valid for `groups`: same group id AND exactly the same set of entity keys. A group whose
    membership changed (an entity was added/merged away) is NOT carried - it must be re-reviewed.
    Returns {group_id: decision}.
    """
    prev_by_id = {p["id"]: p for p in previous if p.get("decision") in ("merge", "dont_merge")}
    out: Dict[str, str] = {}
    for g in groups:
        p = prev_by_id.get(g.id)
        if p is not None and set(p["keys"]) == {e.key for e in g.entities}:
            out[g.id] = p["decision"]
    return out


def previous_decided_groups_not_in(groups: List[Group], previous: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Previously decided groups that the current scan did not rediscover (e.g. a smaller
    max_entities_to_check this time) - they must be kept so ticks are never silently dropped."""
    found = {g.id for g in groups}
    return [p for p in previous if p.get("decision") in ("merge", "dont_merge") and p["id"] not in found]


UNDECIDED_SKIP = "skip"
UNDECIDED_MERGE = "merge"


def select_groups_to_merge(parsed: List[Dict[str, Any]], undecided_policy: str = UNDECIDED_SKIP) -> List[Dict[str, Any]]:
    """
    Groups to actually merge: every `merge`-ticked group, plus (policy "merge") every undecided one -
    the "merge most, tick dont-merge on the exceptions" workflow. `dont_merge` and `conflict` are never
    merged. If a group id appears more than once (e.g. leftovers across files) the first wins.
    """
    if undecided_policy not in (UNDECIDED_SKIP, UNDECIDED_MERGE):
        raise ValueError(f"Unknown undecided_policy: {undecided_policy}")
    wanted = {"merge"} | ({"undecided"} if undecided_policy == UNDECIDED_MERGE else set())
    seen, result = set(), []
    for g in parsed:
        if g["decision"] in wanted and g["id"] not in seen:
            seen.add(g["id"])
            result.append(g)
    return result
