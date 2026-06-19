from __future__ import annotations

import re
from typing import Any, Iterable

from app.graph.normalizers import KINSHIP_RULES, normalize_kinship_person
from app.ingestion.preprocess_qiaopi_wide_table import (
    COMMON_FORMULAE,
    COUNTRY_OR_REGION_BY_PLACE,
    HONORIFIC_TERMS,
    MONEY_MENTION_PATTERN,
    PLACE_ALIASES,
    chinese_integer_to_number,
    normalize_currency,
)
from app.nlp.text_normalizer import NormalizedText, normalize_qiaopi_text_with_mapping
from app.utils.date_normalizer import normalize_qiaopi_date


ENTITY_RULE_VERSION = "qiaopi-entity-rules-1.0.0"
_PERSON_FIELD_RE = re.compile(
    r"(?m)^(?P<label>寄批人|收批人|寄件人|收件人)\s*[:：]\s*(?P<value>[^\n]{1,80})"
)
_DATE_RE = re.compile(
    r"(?:"
    r"(?:中华|中華)?民[国國][零〇一二两三四五六七八九十拾廿卅壹贰貳叁參肆伍陆陸柒捌玖\d]+年"
    r"[^\n，。；]{0,18}"
    r"|(?:18|19|20)\d{2}(?:[年./-]\s*\d{1,2})?(?:[月./-]\s*\d{1,2}\s*(?:日|号|號)?)?"
    r"|[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]?"
    r"[^\n，。；]{0,12}(?:日|号|號)"
    r"|[正元冬腊臘阳陽一二两三四五六七八九十拾壹贰貳叁參肆伍陆陸柒捌玖\d]{1,3}月"
    r"(?:初|廿|卅)?[一二三四五六七八九十拾壹贰貳叁參肆伍陆陸柒捌玖\d]{1,3}"
    r"(?:日|号|號)"
    r")"
)
_PREFIX_PLACE_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"(?:^|[，,\s])(?P<alias>叻)(?=[\u4e00-\u9fff\[]|港|埠|坡)"), "叻", "新加坡"),
    (re.compile(r"(?:^|[在往赴下抵来回，,\s])(?P<alias>暹)(?=[\u4e00-\u9fff\[])"), "暹", "泰国"),
    (re.compile(r"(?:^|[在往赴下抵来回，,\s])(?P<alias>越)(?=[\u4e00-\u9fff\[])"), "越", "越南"),
)


def extract_entities(
    text: str,
    normalized: NormalizedText | None = None,
) -> list[dict[str, Any]]:
    bundle = normalized or normalize_qiaopi_text_with_mapping(text)
    normalized_text = bundle.normalized_text
    candidates: list[dict[str, Any]] = []

    candidates.extend(_extract_people(bundle))
    candidates.extend(_extract_kinship(bundle))
    candidates.extend(_extract_places(bundle))
    candidates.extend(_extract_money(bundle))
    candidates.extend(_extract_dates(bundle))
    candidates.extend(_extract_formulae(bundle))

    selected = _deduplicate_candidates(candidates)
    selected.sort(key=lambda item: (item["normalized_start"], item["normalized_end"], item["entity_type"]))
    for index, item in enumerate(selected, start=1):
        item["entity_id"] = f"ENT-{index:03d}"
    return selected


def _extract_people(bundle: NormalizedText) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for match in _PERSON_FIELD_RE.finditer(bundle.normalized_text):
        raw_value = match.group("value").strip(" ，,。；;")
        if not raw_value:
            continue
        value_start = match.start("value")
        value_end = value_start + len(raw_value)
        role = "sender" if match.group("label") in {"寄批人", "寄件人"} else "recipient"
        results.append(
            _entity(
                bundle,
                entity_type="person",
                value=raw_value,
                normalized_start=value_start,
                normalized_end=value_end,
                confidence=0.96,
                needs_review=False,
                rule_id=f"metadata_{role}",
                attributes={"role": role},
            )
        )
    return results


def _extract_kinship(bundle: NormalizedText) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_spans: set[tuple[int, int]] = set()
    for rule in KINSHIP_RULES:
        start = 0
        while True:
            index = bundle.normalized_text.find(rule.term, start)
            if index < 0:
                break
            end = index + len(rule.term)
            start = index + 1
            if (index, end) in seen_spans:
                continue
            if len(rule.term) == 1 and not _single_character_kinship_context(
                bundle.normalized_text, index, end
            ):
                continue
            normalized = normalize_kinship_person(
                rule.term,
                source_field="kinship_terms",
                entity_type="kinship",
            )
            review = normalized.needs_review or len(rule.term) == 1
            confidence = min(normalized.confidence, 0.72) if len(rule.term) == 1 else normalized.confidence
            results.append(
                _entity(
                    bundle,
                    entity_type="kinship",
                    value=normalized.standard_label,
                    normalized_start=index,
                    normalized_end=end,
                    confidence=confidence,
                    needs_review=review,
                    rule_id=f"kinship:{normalized.kinship_type}",
                    attributes={
                        "kinship_type": normalized.kinship_type,
                        "person_kind": normalized.person_kind,
                        "detected_terms": list(normalized.detected_terms),
                    },
                )
            )
            seen_spans.add((index, end))
    return results


def _extract_places(bundle: NormalizedText) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    aliases = sorted(PLACE_ALIASES.items(), key=lambda item: (-len(item[0]), item[0]))
    for alias, normalized_place in aliases:
        for match in re.finditer(re.escape(alias), bundle.normalized_text):
            results.append(
                _entity(
                    bundle,
                    entity_type="place",
                    value=normalized_place,
                    normalized_start=match.start(),
                    normalized_end=match.end(),
                    confidence=0.94 if alias == normalized_place else 0.9,
                    needs_review=False,
                    rule_id=f"place_alias:{alias}",
                    attributes={
                        "alias": alias,
                        "country_or_region": COUNTRY_OR_REGION_BY_PLACE.get(
                            normalized_place, ""
                        ),
                    },
                )
            )
    for pattern, alias, normalized_place in _PREFIX_PLACE_PATTERNS:
        for match in pattern.finditer(bundle.normalized_text):
            results.append(
                _entity(
                    bundle,
                    entity_type="place",
                    value=normalized_place,
                    normalized_start=match.start("alias"),
                    normalized_end=match.end("alias"),
                    confidence=0.74,
                    needs_review=True,
                    rule_id=f"place_prefix:{alias}",
                    attributes={
                        "alias": alias,
                        "country_or_region": COUNTRY_OR_REGION_BY_PLACE.get(
                            normalized_place, ""
                        ),
                    },
                )
            )
    return results


def _extract_money(bundle: NormalizedText) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for match in MONEY_MENTION_PATTERN.finditer(bundle.normalized_text):
        amount_body = match.group("amount") or ""
        unit = match.group("unit") or ""
        parsed = chinese_integer_to_number(amount_body)
        if parsed is not None and unit in {"万元", "萬元"}:
            parsed *= 10000
        currency = normalize_currency(match.group("currency") or "", unit)
        display_unit = "元" if unit in {"圆", "圓"} else unit
        value = f"{parsed if parsed is not None else amount_body}{display_unit}"
        results.append(
            _entity(
                bundle,
                entity_type="money",
                value=value,
                normalized_start=match.start(),
                normalized_end=match.end(),
                confidence=0.94 if parsed is not None else 0.72,
                needs_review=parsed is None,
                rule_id="money_mention",
                attributes={
                    "amount_number": parsed,
                    "amount_text": f"{amount_body}{unit}",
                    "currency": currency,
                },
            )
        )
    return results


def _extract_dates(bundle: NormalizedText) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for match in _DATE_RE.finditer(bundle.normalized_text):
        source = match.group(0).strip()
        if not source:
            continue
        start = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
        end = start + len(source)
        normalized_date = normalize_qiaopi_date(source)
        value = normalized_date.date_standard or source
        results.append(
            _entity(
                bundle,
                entity_type="date",
                value=value,
                normalized_start=start,
                normalized_end=end,
                confidence=normalized_date.date_parse_confidence,
                needs_review=(
                    normalized_date.date_parse_confidence < 0.8
                    or normalized_date.date_precision in {"unknown", "month_day_no_year"}
                ),
                rule_id="qiaopi_date",
                attributes=normalized_date.as_db_fields(),
            )
        )
    return results


def _extract_formulae(bundle: NormalizedText) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    formulae = sorted(set([*COMMON_FORMULAE, *HONORIFIC_TERMS]), key=lambda value: (-len(value), value))
    for formula in formulae:
        for match in re.finditer(re.escape(formula), bundle.normalized_text):
            results.append(
                _entity(
                    bundle,
                    entity_type="style_formula",
                    value=formula,
                    normalized_start=match.start(),
                    normalized_end=match.end(),
                    confidence=0.9,
                    needs_review=False,
                    rule_id=f"formula:{formula}",
                    attributes={},
                )
            )
    return results


def _entity(
    bundle: NormalizedText,
    *,
    entity_type: str,
    value: str,
    normalized_start: int,
    normalized_end: int,
    confidence: float,
    needs_review: bool,
    rule_id: str,
    attributes: dict[str, Any],
) -> dict[str, Any]:
    original_start, original_end = bundle.original_span(normalized_start, normalized_end)
    return {
        "entity_id": "",
        "entity_type": entity_type,
        "value": str(value),
        "source_text": bundle.original_text[original_start:original_end],
        "normalized_source_text": bundle.normalized_text[normalized_start:normalized_end],
        "original_start": original_start,
        "original_end": original_end,
        "normalized_start": normalized_start,
        "normalized_end": normalized_end,
        "extractor": "rule",
        "extractor_version": ENTITY_RULE_VERSION,
        "rule_id": rule_id,
        "confidence": round(max(0.0, min(1.0, float(confidence))), 4),
        "needs_review": bool(needs_review),
        "attributes": attributes,
    }


def _deduplicate_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        candidates,
        key=lambda item: (
            item["normalized_start"],
            -(item["normalized_end"] - item["normalized_start"]),
            -item["confidence"],
            item["entity_type"],
        ),
    )
    selected: list[dict[str, Any]] = []
    exact_keys: set[tuple[str, int, int, str]] = set()
    for candidate in ordered:
        key = (
            candidate["entity_type"],
            candidate["normalized_start"],
            candidate["normalized_end"],
            candidate["value"],
        )
        if key in exact_keys:
            continue
        if any(
            existing["entity_type"] == candidate["entity_type"]
            and candidate["normalized_start"] >= existing["normalized_start"]
            and candidate["normalized_end"] <= existing["normalized_end"]
            for existing in selected
        ):
            continue
        exact_keys.add(key)
        selected.append(candidate)
    return selected


def _single_character_kinship_context(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start else ""
    after = text[end] if end < len(text) else ""
    separators = " \n，,。；;：:、（）()【】[]"
    if not before or before in separators or not after or after in separators:
        return True
    context = text[max(0, start - 2) : min(len(text), end + 4)]
    return any(
        marker in context
        for marker in (
            "大人",
            "尊前",
            "膝下",
            "谨",
            "叩",
            "启",
            "寄批人",
            "收批人",
        )
    )
