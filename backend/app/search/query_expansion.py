from __future__ import annotations

import re
from dataclasses import dataclass


WeightedTerms = dict[str, tuple[str, ...]]


EXPANSION_DICTIONARY: dict[str, WeightedTerms] = {
    "母亲": {
        "strong": ("慈亲", "家慈", "萱堂", "家母"),
        "medium": ("大人", "膝下", "阿母", "阿妈"),
        "weak": ("严慈",),
    },
    "父亲": {
        "strong": ("严亲", "家父"),
        "medium": ("双亲", "大人", "膝下"),
        "weak": ("严慈",),
    },
    "双亲": {
        "strong": ("父母", "严慈"),
        "medium": ("大人", "膝下", "慈亲", "严亲"),
        "weak": (),
    },
    "祖母": {
        "strong": ("太母", "阿嬷"),
        "medium": ("慈亲",),
        "weak": ("大人",),
    },
    "妻子": {
        "strong": ("妻", "贤妻", "内人"),
        "medium": ("家眷",),
        "weak": (),
    },
    "儿子": {
        "strong": ("儿", "男", "小儿"),
        "medium": ("子",),
        "weak": (),
    },
    "寄款": {
        "strong": ("批款", "寄上", "汇上"),
        "medium": ("付去", "兹托", "带去", "奉上"),
        "weak": ("批局",),
    },
    "汇款": {
        "strong": ("批款", "寄上", "汇上"),
        "medium": ("付去", "兹托", "带去", "奉上"),
        "weak": ("批局",),
    },
    "查收": {
        "strong": ("收讫", "照收", "如数查收"),
        "medium": ("收用", "检收", "祈收"),
        "weak": ("查明",),
    },
    "平安": {
        "strong": ("安好", "无恙", "清泰"),
        "medium": ("勿念", "毋念", "起居"),
        "weak": ("安康",),
    },
    "保重": {
        "strong": ("珍重", "身体", "安康"),
        "medium": ("调养", "起居"),
        "weak": ("勿念",),
    },
    "读书": {
        "strong": ("勤读", "勤学", "学业"),
        "medium": ("书馆", "课程", "成绩", "温习"),
        "weak": ("教训", "务望"),
    },
    "勤俭": {
        "strong": ("勤俭", "节俭"),
        "medium": ("持家", "省用"),
        "weak": ("教训", "务望"),
    },
    "工作": {
        "strong": ("谋生", "营生", "工资"),
        "medium": ("生计", "职业"),
        "weak": ("事务",),
    },
    "生病": {
        "strong": ("病", "疾", "医药"),
        "medium": ("痊安", "调养", "身体"),
        "weak": ("安康",),
    },
    "新加坡": {
        "strong": ("星洲", "叻坡", "石叻", "叻"),
        "medium": ("南洋",),
        "weak": ("外洋",),
    },
    "香港": {
        "strong": ("港",),
        "medium": ("港地",),
        "weak": (),
    },
    "泰国": {
        "strong": ("暹罗", "暹"),
        "medium": (),
        "weak": (),
    },
    "越南": {
        "strong": ("安南", "西贡"),
        "medium": (),
        "weak": (),
    },
    "马来西亚": {
        "strong": ("马来亚", "槟城", "吉隆坡"),
        "medium": ("南洋",),
        "weak": (),
    },
}

PUNCTUATION_PATTERN = re.compile(r"[\s\r\n\t；;，,、。！？!?：:（）()【】\[\]《》<>“”\"'‘’/|\\]+")
FTS_DANGEROUS_PATTERN = re.compile(r"[\?\^\*\~\{\}=+\-]+")


@dataclass(frozen=True)
class QueryExpansion:
    original_query: str
    normalized_query: str
    expanded_query: str
    original_terms: list[str]
    strong_expansion_terms: list[str]
    medium_expansion_terms: list[str]
    weak_expansion_terms: list[str]
    expansion_terms: list[str]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped_values: list[str] = []
    for value in values:
        clean_value = value.strip()
        if not clean_value or clean_value in seen:
            continue
        seen.add(clean_value)
        deduped_values.append(clean_value)
    return deduped_values


def _dedupe_without(values: list[str], excluded: set[str]) -> list[str]:
    return [value for value in _dedupe(values) if value not in excluded]


def normalize_query(query: str) -> str:
    cleaned = FTS_DANGEROUS_PATTERN.sub(" ", query or "")
    cleaned = PUNCTUATION_PATTERN.sub(" ", cleaned)
    return " ".join(cleaned.split())


def tokenize_query(query: str) -> list[str]:
    normalized = normalize_query(query)
    if not normalized:
        return []
    return normalized.split()


def expand_query(query: str) -> QueryExpansion:
    original_query = query or ""
    normalized_query = normalize_query(original_query)
    original_terms = tokenize_query(normalized_query)

    strong_terms: list[str] = []
    medium_terms: list[str] = []
    weak_terms: list[str] = []
    for term in original_terms:
        weighted_terms = EXPANSION_DICTIONARY.get(term, {})
        strong_terms.extend(weighted_terms.get("strong", ()))
        medium_terms.extend(weighted_terms.get("medium", ()))
        weak_terms.extend(weighted_terms.get("weak", ()))

    original_terms = _dedupe(original_terms)
    original_set = set(original_terms)
    strong_terms = _dedupe(strong_terms)
    medium_terms = _dedupe_without(medium_terms, original_set | set(strong_terms))
    weak_terms = _dedupe_without(weak_terms, original_set | set(strong_terms) | set(medium_terms))
    expansion_terms = _dedupe_without([*strong_terms, *medium_terms, *weak_terms], original_set)
    expanded_terms = _dedupe([*original_terms, *strong_terms, *medium_terms, *weak_terms])

    return QueryExpansion(
        original_query=original_query,
        normalized_query=normalized_query,
        expanded_query=" ".join(expanded_terms),
        original_terms=original_terms,
        strong_expansion_terms=strong_terms,
        medium_expansion_terms=medium_terms,
        weak_expansion_terms=weak_terms,
        expansion_terms=expansion_terms,
    )


def terms_for_expansion_mode(
    expansion: QueryExpansion,
    expansion_mode: str,
    stage: int | None = None,
) -> list[str]:
    mode = expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced"
    if mode == "strict":
        return _dedupe([*expansion.original_terms, *expansion.strong_expansion_terms])
    if mode == "broad":
        return _dedupe(
            [
                *expansion.original_terms,
                *expansion.strong_expansion_terms,
                *expansion.medium_expansion_terms,
                *expansion.weak_expansion_terms,
            ]
        )
    if stage == 1:
        return _dedupe([*expansion.original_terms, *expansion.strong_expansion_terms])
    if stage == 2:
        return _dedupe(
            [
                *expansion.original_terms,
                *expansion.strong_expansion_terms,
                *expansion.medium_expansion_terms,
            ]
        )
    return _dedupe(
        [
            *expansion.original_terms,
            *expansion.strong_expansion_terms,
            *expansion.medium_expansion_terms,
            *expansion.weak_expansion_terms,
        ]
    )
