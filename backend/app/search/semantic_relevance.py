from __future__ import annotations

import re
from typing import Any, Iterable, Mapping


SEMANTIC_GUARD_TERMS: dict[str, tuple[str, ...]] = {
    "母亲": (
        "母亲",
        "慈亲",
        "家慈",
        "家母",
        "萱堂",
        "阿母",
        "阿妈",
        "慈母",
        "娘亲",
        "姆母",
    ),
    "宋树钊": (
        "宋树钊",
        "叻宋树钊",
    ),
    "读书": (
        "读书",
        "勤读",
        "勤学",
        "学业",
        "功课",
        "课程",
        "成绩",
        "温习",
        "学习",
        "求学",
        "从学",
        "书馆",
        "书法",
        "英文",
        "用心学习",
    ),
    "求学": (
        "读书",
        "勤读",
        "勤学",
        "学业",
        "功课",
        "课程",
        "成绩",
        "温习",
        "学习",
        "求学",
        "从学",
        "书馆",
        "书法",
        "英文",
        "用心学习",
    ),
    "成婚": (
        "完婚",
        "婚事",
        "定婚",
        "订婚",
        "迎娶",
        "婚姻",
        "结婚",
        "婚配",
        "嫁娶",
        "聘定",
        "放媒",
        "出嫁",
    ),
    "婚事": (
        "完婚",
        "婚事",
        "定婚",
        "订婚",
        "迎娶",
        "婚姻",
        "结婚",
        "婚配",
        "嫁娶",
        "聘定",
        "放媒",
        "出嫁",
    ),
    "婚礼": (
        "完婚",
        "婚事",
        "迎娶",
        "婚姻",
        "结婚",
        "婚配",
        "嫁娶",
        "聘定",
        "放媒",
        "出嫁",
    ),
    "结婚": (
        "完婚",
        "婚事",
        "定婚",
        "订婚",
        "迎娶",
        "婚姻",
        "结婚",
        "婚配",
        "嫁娶",
        "聘定",
        "放媒",
        "出嫁",
    ),
    "嫁娶": (
        "完婚",
        "婚事",
        "定婚",
        "订婚",
        "迎娶",
        "婚姻",
        "结婚",
        "婚配",
        "嫁娶",
        "聘定",
        "放媒",
        "出嫁",
    ),
}

SEMANTIC_EXCLUSION_TERMS: dict[str, tuple[str, ...]] = {
    "母亲": (
        "岳母",
        "岳慈亲",
        "岳父母",
        "岳祖母",
        "岳祖父",
        "岳祖父母",
        "祖母",
        "祖父",
        "祖父母",
        "祖慈",
        "外祖母",
        "外祖父",
        "外祖父母",
        "阿嬷",
        "阿嫲",
        "奶奶",
        "阿公",
        "爷爷",
    ),
}

SEMANTIC_GUARD_FIELDS: tuple[str, ...] = (
    "unit_text",
    "matched_text",
    "title_reference",
    "sender",
    "recipient",
    "kinship_terms",
    "primary_kinship",
    "opening_salutation",
    "retrieval_keywords",
    "theme_tags",
    "main_intent",
    "style_keywords",
)

STRICT_ENTITY_QUERY_TERMS: tuple[str, ...] = (
    "宋树钊",
)

LOW_INFORMATION_UNIT_TYPES: frozenset[str] = frozenset(
    {
        "opening",
        "closing",
        "salutation",
        "signature",
        "date",
    }
)

_COMPACT_RE = re.compile(r"[\s，。！？；：、,.!?;:（）()《》【】\[\]\"'“”‘’]+")


def semantic_guard_terms(query: str) -> tuple[str, ...]:
    clean_query = "".join(str(query or "").split())
    terms: list[str] = []
    seen: set[str] = set()
    for trigger, guard_terms in SEMANTIC_GUARD_TERMS.items():
        if trigger not in clean_query:
            continue
        for term in guard_terms:
            if term in seen:
                continue
            seen.add(term)
            terms.append(term)
    return tuple(terms)


def semantic_exclusion_terms(query: str | None) -> tuple[str, ...]:
    clean_query = "".join(str(query or "").split())
    terms: list[str] = []
    seen: set[str] = set()
    for trigger, exclusion_terms in SEMANTIC_EXCLUSION_TERMS.items():
        if trigger not in clean_query:
            continue
        for term in exclusion_terms:
            if term in seen:
                continue
            seen.add(term)
            terms.append(term)
    return tuple(terms)


def _compact_text(value: str) -> str:
    return _COMPACT_RE.sub("", value)


def _strict_entity_query(query: str | None) -> bool:
    clean_query = "".join(str(query or "").split())
    return any(term in clean_query for term in STRICT_ENTITY_QUERY_TERMS)


def semantic_guard_text(row: Mapping[str, Any]) -> str:
    return "\n".join(
        str(row.get(field_name) or "")
        for field_name in SEMANTIC_GUARD_FIELDS
    )


def _row_matches_strict_entity_guard(
    row: Mapping[str, Any],
    guard_terms: tuple[str, ...],
) -> bool:
    """Reject semantically-related but low-value snippets for exact names.

    A person-name query can match record titles and then surface tiny opening or
    closing units such as "男树钊禀". These are traceable, but poor as search
    cards. Keep substantial record/body evidence and exact content matches;
    drop short formulaic units.
    """

    unit_type = str(row.get("unit_type") or "").strip()
    unit_text = str(row.get("unit_text") or "")
    matched_text = str(row.get("matched_text") or "")
    content_text = f"{unit_text}\n{matched_text}"

    if unit_type in LOW_INFORMATION_UNIT_TYPES:
        return False

    compact_content_text = _compact_text(content_text)
    if any(term in content_text for term in guard_terms):
        return True

    # If the title/metadata proves the entity but the unit body is substantial,
    # it is still useful as a record-level search result. Short snippets are not.
    if unit_type == "style_reference":
        return len(compact_content_text) >= 16
    return len(compact_content_text) >= 80


def row_matches_semantic_guard(
    row: Mapping[str, Any],
    guard_terms: Iterable[str],
    query: str | None = None,
) -> bool:
    terms = tuple(term for term in guard_terms if term)
    if not terms:
        return True
    haystack = semantic_guard_text(row)
    excluded_terms = semantic_exclusion_terms(query)
    if excluded_terms and any(term in haystack for term in excluded_terms):
        return False
    if not any(term in haystack for term in terms):
        return False
    if _strict_entity_query(query):
        return _row_matches_strict_entity_guard(row, terms)
    return True
