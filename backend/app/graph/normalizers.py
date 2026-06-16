from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


_PUNCTUATION_RE = re.compile(r"[\s\u3000,，.。;；:：、!！?？\"'`“”‘’（）()\[\]【】{}<>《》/\\|]+")
_SEPARATOR_RE = re.compile(r"[;；,，、\n\r\t]+")
_AMOUNT_RE = re.compile(r"[\s\u3000,，.。;；:：、!！?？\"'`“”‘’（）()\[\]【】{}<>《》/\\|]+")

PLACE_ALIASES: dict[str, str] = {
    "叻": "新加坡",
    "叻埠": "新加坡",
    "石叻": "新加坡",
    "星洲": "新加坡",
    "暹罗": "泰国",
    "安南": "越南",
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ")
    return unicodedata.normalize("NFKC", text).strip()


def split_multi_value(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return [part.strip() for part in _SEPARATOR_RE.split(text) if part.strip()]


def normalize_person_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    return _PUNCTUATION_RE.sub("", text)


def normalize_place_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    compact = _PUNCTUATION_RE.sub("", text)
    return PLACE_ALIASES.get(compact, compact)


def normalize_theme_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    compact = re.sub(r"[\s\u3000]+", "", text)
    if compact.isascii():
        return compact.lower()
    return compact


def normalize_date_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    return re.sub(r"[\s\u3000]+", "", text)


def normalize_amount_raw(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    return _AMOUNT_RE.sub("", text)


def normalize_amount_number(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def is_uncertain_date(label: Any) -> bool:
    text = clean_text(label)
    if not text:
        return True
    return any(marker in text for marker in ("不详", "未详", "约", "?", "？", "[", "]", "〔", "〕"))


KINSHIP_TERM = "kinship_term"
NAMED_PERSON = "named_person"
UNKNOWN_PERSON_KIND = "unknown"
NO_KINSHIP_TYPE = "none"
UNKNOWN_KINSHIP_TYPE = "unknown"

KINSHIP_SOURCE_FIELDS = {
    "kinship_terms",
    "recipient",
    "recipient_name_clean",
}
KINSHIP_REVIEW_SOURCE_FIELDS = {"kinship_terms"}
KINSHIP_SIGNATURE_SOURCE_FIELDS = {"sender", "sender_name_clean"}
KINSHIP_ENTITY_TYPES = {"kinship"}


@dataclass(frozen=True)
class KinshipNormalization:
    raw_label: str
    raw_labels: tuple[str, ...]
    normalized_label: str
    person_kind: str
    kinship_type: str
    normalization_note: str
    confidence: float
    needs_review: bool
    detected_terms: tuple[str, ...] = ()
    is_collective_kinship: bool = False
    member_labels: tuple[str, ...] = ()
    member_kinship_types: tuple[str, ...] = ()

    @property
    def standard_label(self) -> str:
        return self.normalized_label


@dataclass(frozen=True)
class KinshipRule:
    term: str
    normalized_label: str
    kinship_type: str
    match_mode: str = "embedded"
    requires_context: bool = False
    confidence: float = 0.95


KINSHIP_RULES: tuple[KinshipRule, ...] = tuple(
    sorted(
        (
            KinshipRule("岳祖父母", "岳祖父母", "grandparents_in_law"),
            KinshipRule("外祖父母", "外祖父母", "maternal_grandparents"),
            KinshipRule("祖父母", "祖父母", "grandparents"),
            KinshipRule("岳父母", "岳父母", "parents_in_law"),
            KinshipRule("岳双亲", "岳父母", "parents_in_law"),
            KinshipRule("外祖母", "外祖母", "maternal_grandmother"),
            KinshipRule("外祖父", "外祖父", "maternal_grandfather"),
            KinshipRule("岳祖母", "岳祖母", "grandmother_in_law"),
            KinshipRule("岳祖父", "岳祖父", "grandfather_in_law"),
            KinshipRule("母亲大人", "母亲", "mother"),
            KinshipRule("父亲大人", "父亲", "father"),
            KinshipRule("慈亲大人", "母亲", "mother"),
            KinshipRule("严亲大人", "父亲", "father"),
            KinshipRule("岳慈亲", "岳母", "mother_in_law"),
            KinshipRule("吾妻", "妻子", "wife"),
            KinshipRule("贤妻", "妻子", "wife"),
            KinshipRule("荆妻", "妻子", "wife"),
            KinshipRule("内妻", "妻子", "wife"),
            KinshipRule("妻室", "妻子", "wife"),
            KinshipRule("内人", "妻子", "wife"),
            KinshipRule("拙荆", "妻子", "wife"),
            KinshipRule("爱妻", "妻子", "wife"),
            KinshipRule("慈亲", "母亲", "mother"),
            KinshipRule("慈母", "母亲", "mother"),
            KinshipRule("母亲", "母亲", "mother"),
            KinshipRule("家慈", "母亲", "mother"),
            KinshipRule("严亲", "父亲", "father"),
            KinshipRule("严父", "父亲", "father"),
            KinshipRule("父亲", "父亲", "father"),
            KinshipRule("家严", "父亲", "father"),
            KinshipRule("双亲", "双亲", "parents"),
            KinshipRule("父母", "双亲", "parents"),
            KinshipRule("二亲", "双亲", "parents"),
            KinshipRule("祖母", "祖母", "grandmother"),
            KinshipRule("祖慈", "祖母", "grandmother"),
            KinshipRule("祖父", "祖父", "grandfather"),
            KinshipRule("岳母", "岳母", "mother_in_law"),
            KinshipRule("岳父", "岳父", "father_in_law"),
            KinshipRule("兄长", "兄长", "elder_brother"),
            KinshipRule("胞兄", "兄长", "elder_brother"),
            KinshipRule("吾兄", "兄长", "elder_brother"),
            KinshipRule("兄台", "兄长", "elder_brother"),
            KinshipRule("姻兄", "兄长", "elder_brother"),
            KinshipRule("表兄", "兄长", "elder_brother"),
            KinshipRule("大兄", "兄长", "elder_brother"),
            KinshipRule("胞弟", "弟弟", "younger_brother"),
            KinshipRule("下蓬英弟", "弟弟", "younger_brother"),
            KinshipRule("逞大弟", "弟弟", "younger_brother"),
            KinshipRule("吾弟", "弟弟", "younger_brother"),
            KinshipRule("贤弟", "弟弟", "younger_brother"),
            KinshipRule("大弟", "弟弟", "younger_brother"),
            KinshipRule("姻弟", "弟弟", "younger_brother"),
            KinshipRule("英弟", "弟弟", "younger_brother"),
            KinshipRule("吾姊", "姐姐", "elder_sister"),
            KinshipRule("姻姊", "姐姐", "elder_sister"),
            KinshipRule("大姊", "姐姐", "elder_sister"),
            KinshipRule("姊", "姐姐", "elder_sister", match_mode="exact_or_context"),
            KinshipRule("姐", "姐姐", "elder_sister", match_mode="exact_or_context"),
            KinshipRule("胞妹", "妹妹", "younger_sister"),
            KinshipRule("贤妹", "妹妹", "younger_sister"),
            KinshipRule("妹", "妹妹", "younger_sister", match_mode="exact_or_context"),
            KinshipRule("侄儿", "侄子", "nephew"),
            KinshipRule("族侄台", "侄子", "nephew"),
            KinshipRule("贤侄", "侄子", "nephew"),
            KinshipRule("族侄", "侄子", "nephew"),
            KinshipRule("宗侄", "侄子", "nephew"),
            KinshipRule("侄台", "侄子", "nephew"),
            KinshipRule("吾侄", "侄子", "nephew"),
            KinshipRule("内侄", "侄子", "nephew"),
            KinshipRule("两侄", "侄子", "nephew"),
            KinshipRule("侄", "侄子", "nephew", match_mode="suffix_or_context"),
            KinshipRule("细姨母", "姨母", "aunt_maternal"),
            KinshipRule("姨母", "姨母", "aunt_maternal"),
            KinshipRule("嫂嫂", "嫂子", "sister_in_law"),
            KinshipRule("表嫂", "嫂子", "sister_in_law"),
            KinshipRule("大嫂", "嫂子", "sister_in_law"),
            KinshipRule("嫂", "嫂子", "sister_in_law", match_mode="exact_or_context"),
            KinshipRule("女儿", "女儿", "daughter"),
            KinshipRule("吾儿", "儿子", "son"),
            KinshipRule("孩儿", "儿子", "son"),
            KinshipRule("儿", "儿子", "son", match_mode="exact_or_context"),
            KinshipRule("男", "儿子", "son", match_mode="exact", requires_context=True),
            KinshipRule("兄", "兄长", "elder_brother", match_mode="exact_or_context"),
            KinshipRule("弟", "弟弟", "younger_brother", match_mode="exact_or_context"),
            KinshipRule("妻", "妻子", "wife", match_mode="exact_or_context"),
            KinshipRule("叔父", "叔父", "uncle"),
            KinshipRule("叔", "叔父", "uncle", match_mode="exact_or_context"),
        ),
        key=lambda rule: (-len(rule.term), rule.term),
    )
)

AMBIGUOUS_KINSHIP_TERMS: tuple[str, ...] = ()

COLLECTIVE_KINSHIP_MEMBERS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "parents": (("父亲", "母亲"), ("father", "mother")),
    "parents_in_law": (("岳父", "岳母"), ("father_in_law", "mother_in_law")),
    "maternal_grandparents": (
        ("外祖父", "外祖母"),
        ("maternal_grandfather", "maternal_grandmother"),
    ),
    "grandparents": (("祖父", "祖母"), ("grandfather", "grandmother")),
    "grandparents_in_law": (
        ("岳祖父", "岳祖母"),
        ("grandfather_in_law", "grandmother_in_law"),
    ),
}

KINSHIP_SPLIT_GROUPS: tuple[tuple[str, tuple[KinshipRule, ...]], ...] = (
    (
        "岳祖母岳慈亲",
        (
            KinshipRule("岳祖母", "岳祖母", "grandmother_in_law"),
            KinshipRule("岳慈亲", "岳母", "mother_in_law"),
        ),
    ),
    (
        "姻姊姻弟",
        (
            KinshipRule("姻姊", "姐姐", "elder_sister"),
            KinshipRule("姻弟", "弟弟", "younger_brother"),
        ),
    ),
)


def normalize_kinship_person(
    label: Any,
    raw_labels: list[str] | None = None,
    *,
    entity_type: str = "",
    source_field: str = "",
    person_kind_hint: str = "",
) -> KinshipNormalization:
    return normalize_kinship_people(
        label,
        raw_labels=raw_labels,
        entity_type=entity_type,
        source_field=source_field,
        person_kind_hint=person_kind_hint,
    )[0]


def normalize_kinship_people(
    label: Any,
    raw_labels: list[str] | None = None,
    *,
    entity_type: str = "",
    source_field: str = "",
    person_kind_hint: str = "",
) -> list[KinshipNormalization]:
    labels = _candidate_person_labels(label, raw_labels or [])
    raw_label = labels[0] if labels else normalize_person_label(label)
    has_kinship_context = _has_kinship_context(
        entity_type=entity_type,
        source_field=source_field,
        person_kind_hint=person_kind_hint,
    )
    has_signature_context = _has_kinship_signature_context(
        entity_type=entity_type,
        source_field=source_field,
        person_kind_hint=person_kind_hint,
    )
    has_review_context = _has_kinship_review_context(
        entity_type=entity_type,
        source_field=source_field,
        person_kind_hint=person_kind_hint,
    )
    ambiguous_terms = _detected_ambiguous_terms(labels)
    split_results = _split_kinship_results(labels, raw_label)
    if split_results:
        return split_results
    candidates = _detect_kinship_candidates(
        labels,
        has_kinship_context,
        has_signature_context,
    )

    if candidates:
        best = candidates[0]
        detected_terms = _dedupe_strings(
            [candidate.term for candidate in candidates] + ambiguous_terms
        )
        detected_types = {
            candidate.kinship_type
            for candidate in candidates
            if candidate.kinship_type != best.kinship_type
        }
        needs_review = bool(ambiguous_terms or detected_types)
        confidence = best.confidence
        if needs_review:
            confidence = min(confidence, 0.72)
        return [
            _kinship_result(
                rule=best,
                raw_label=raw_label,
                labels=labels,
                detected_terms=detected_terms,
                confidence=confidence,
                needs_review=needs_review,
            )
        ]

    if has_review_context or ambiguous_terms:
        return [
            KinshipNormalization(
                raw_label=raw_label,
                raw_labels=tuple(labels),
                normalized_label=raw_label,
                person_kind=UNKNOWN_PERSON_KIND,
                kinship_type=UNKNOWN_KINSHIP_TYPE,
                normalization_note="Possible kinship term has no configured normalization rule.",
                confidence=0.2,
                needs_review=True,
                detected_terms=tuple(ambiguous_terms),
            )
        ]

    return [
        KinshipNormalization(
            raw_label=raw_label,
            raw_labels=tuple(labels),
            normalized_label=raw_label,
            person_kind=NAMED_PERSON,
            kinship_type=NO_KINSHIP_TYPE,
            normalization_note="Named person; no kinship normalization applied.",
            confidence=1.0,
            needs_review=False,
            detected_terms=(),
        )
    ]


def _candidate_person_labels(label: Any, raw_labels: list[str]) -> list[str]:
    values = [label, *raw_labels]
    return _dedupe_strings(normalize_person_label(value) for value in values if normalize_person_label(value))


def _split_kinship_results(
    labels: list[str],
    raw_label: str,
) -> list[KinshipNormalization]:
    split_rules: list[KinshipRule] = []
    detected_terms: list[str] = []
    if any("岳祖母" in label and "岳慈亲" in label for label in labels):
        split_rules.extend(KINSHIP_SPLIT_GROUPS[0][1])
        detected_terms.extend(("岳祖母", "岳慈亲"))
    if any("姻姊" in label and "姻弟" in label for label in labels):
        split_rules.extend(KINSHIP_SPLIT_GROUPS[1][1])
        detected_terms.extend(("姻姊", "姻弟"))
    if not split_rules:
        return []

    results: list[KinshipNormalization] = []
    seen_types: set[str] = set()
    for rule in split_rules:
        if rule.kinship_type in seen_types:
            continue
        seen_types.add(rule.kinship_type)
        rule_terms = _dedupe_strings([*detected_terms, rule.term])
        results.append(
            _kinship_result(
                rule=rule,
                raw_label=raw_label,
                labels=labels,
                detected_terms=rule_terms,
                confidence=rule.confidence,
                needs_review=False,
                note_suffix=" Compound kinship label split into separate graph nodes.",
            )
        )
    return results


def _detect_kinship_candidates(
    labels: list[str],
    has_kinship_context: bool,
    has_signature_context: bool,
) -> list[KinshipRule]:
    candidates: list[KinshipRule] = []
    seen_terms: set[str] = set()
    for rule in KINSHIP_RULES:
        if any(rule.term in seen_term for seen_term in seen_terms):
            continue
        if rule.requires_context and not (has_kinship_context or has_signature_context):
            continue
        if any(_rule_matches(rule, label, has_kinship_context) for label in labels):
            if rule.term not in seen_terms:
                seen_terms.add(rule.term)
                candidates.append(rule)
    return candidates


def _kinship_result(
    *,
    rule: KinshipRule,
    raw_label: str,
    labels: list[str],
    detected_terms: list[str],
    confidence: float,
    needs_review: bool,
    note_suffix: str = "",
) -> KinshipNormalization:
    member_labels, member_kinship_types = COLLECTIVE_KINSHIP_MEMBERS.get(
        rule.kinship_type,
        ((), ()),
    )
    return KinshipNormalization(
        raw_label=raw_label,
        raw_labels=tuple(labels),
        normalized_label=rule.normalized_label,
        person_kind=KINSHIP_TERM,
        kinship_type=rule.kinship_type,
        normalization_note=_kinship_note(rule, needs_review) + note_suffix,
        confidence=round(confidence, 4),
        needs_review=needs_review,
        detected_terms=tuple(detected_terms),
        is_collective_kinship=bool(member_labels),
        member_labels=member_labels,
        member_kinship_types=member_kinship_types,
    )


def _rule_matches(rule: KinshipRule, label: str, has_kinship_context: bool) -> bool:
    if rule.match_mode == "exact":
        return label == rule.term
    if rule.match_mode == "exact_or_context":
        return label == rule.term or (has_kinship_context and label.endswith(rule.term))
    if rule.match_mode == "suffix_or_context":
        return label == rule.term or label.endswith(rule.term) or (has_kinship_context and rule.term in label)
    return rule.term in label


def _detected_ambiguous_terms(labels: list[str]) -> list[str]:
    return _dedupe_strings(
        term
        for label in labels
        for term in AMBIGUOUS_KINSHIP_TERMS
        if term in label
    )


def _kinship_note(rule: KinshipRule, needs_review: bool) -> str:
    note = f"Kinship term normalized to {rule.normalized_label} / {rule.kinship_type}."
    if needs_review:
        note += " Multiple or ambiguous kinship terms detected; review recommended."
    return note


def _has_kinship_context(
    *,
    entity_type: str,
    source_field: str,
    person_kind_hint: str,
) -> bool:
    return (
        entity_type in KINSHIP_ENTITY_TYPES
        or source_field in KINSHIP_SOURCE_FIELDS
        or person_kind_hint == KINSHIP_TERM
    )


def _has_kinship_review_context(
    *,
    entity_type: str,
    source_field: str,
    person_kind_hint: str,
) -> bool:
    return (
        entity_type in KINSHIP_ENTITY_TYPES
        or source_field in KINSHIP_REVIEW_SOURCE_FIELDS
        or person_kind_hint == KINSHIP_TERM
    )


def _has_kinship_signature_context(
    *,
    entity_type: str,
    source_field: str,
    person_kind_hint: str,
) -> bool:
    return (
        entity_type in KINSHIP_ENTITY_TYPES
        or source_field in KINSHIP_SIGNATURE_SOURCE_FIELDS
        or person_kind_hint == KINSHIP_TERM
    )


def _dedupe_strings(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
