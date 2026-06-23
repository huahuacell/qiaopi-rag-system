from __future__ import annotations

import re
from typing import Any, Mapping

from app.validation.fact_extractor import extract_facts

LEXICAL_EVIDENCE_MAPPING_VERSION = "lexical-evidence-map-v1"
DUAL_EVIDENCE_MAPPING_VERSION = "dual-evidence-map-v2"
_SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{1,4}|[A-Za-z0-9_.-]+")
_INPUT_SPAN_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")

_SEMANTIC_ALIASES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("慈亲", "家母", "阿母", "妈妈"), "母亲"),
    (("安好", "无恙", "安康", "康健"), "平安"),
    (("勿念", "毋念", "莫念", "莫挂", "挂怀"), "放心"),
    (("汇款", "奉上", "带去", "付去", "捎回"), "寄款"),
    (("收讫", "检收", "照收", "妥收", "收妥"), "查收"),
    (("故里", "故园", "乡里"), "家乡"),
    (("惦念", "挂念", "思念", "想起", "忆及"), "想念"),
    (("珍摄", "珍重", "调养"), "保重"),
    (("习字", "习书", "笔墨"), "练字"),
    (("儿女", "儿子", "女儿", "孩儿"), "孩子"),
    (("过劳", "操劳", "太累", "劳累"), "劳累"),
    (("照应", "照料", "帮忙"), "帮忙"),
    (("回音", "复信", "回覆"), "回信"),
    (("返乡", "归乡", "回家", "回去"), "回乡"),
    (("米粮", "米钱", "口粮"), "米粮"),
    (("添衣", "添衣服", "置衣"), "添衣"),
    (("安顿", "安定", "安稳"), "安顿"),
    (("敬上", "谨上", "谨启", "谨禀", "叩上", "泐", "缄"), "署名"),
)

_STYLE_ONLY_TERMS = ("敬上", "谨上", "谨启", "谨禀", "叩上", "泐", "缄")

_FUNCTIONAL_SLOT_MARKERS: dict[str, tuple[str, ...]] = {
    "safety": (
        "平安",
        "安好",
        "无恙",
        "安康",
        "勿念",
        "放心",
        "住处",
        "寓所",
        "身体",
        "生意",
        "营生",
        "渐顺",
        "顺手",
    ),
    "family_care": (
        "保重",
        "珍重",
        "珍摄",
        "调养",
        "太累",
        "劳苦",
        "劳累",
        "过劳",
    ),
    "instruction": (
        "务必",
        "切勿",
        "不可",
        "记得",
        "盼",
        "回音",
        "回信",
        "照应",
        "帮忙",
        "商量",
        "办理",
        "有事请",
        "可请",
        "祈",
    ),
}


def map_generated_text_to_evidence(
    generated_text: str,
    evidence_references: list[Mapping[str, Any]],
    *,
    input_text: str | None = None,
) -> list[dict[str, Any]]:
    evidence = [
        reference
        for reference in evidence_references
        if str(reference.get("unit_text") or "").strip()
    ]
    if input_text is None:
        return _map_knowledge_evidence_only(generated_text, evidence)
    return _map_content_and_style_evidence(
        generated_text,
        input_text=input_text,
        evidence=evidence,
    )


def _map_knowledge_evidence_only(
    generated_text: str,
    evidence: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for sentence_index, match in enumerate(_SENTENCE_RE.finditer(generated_text), start=1):
        sentence = match.group(0).strip()
        if not sentence or _is_heading(sentence):
            continue
        best_reference, best_score = _best_reference(sentence, evidence)
        supported = best_reference is not None and best_score >= 0.08
        reference = best_reference or {}
        mappings.append(
            {
                "mapping_id": f"MAP-{sentence_index:03d}",
                "target_span": sentence,
                "generated_start": match.start() + len(match.group(0)) - len(match.group(0).lstrip()),
                "generated_end": match.start() + len(match.group(0).rstrip()),
                "record_id": str(reference.get("record_id") or ""),
                "unit_id": str(reference.get("unit_id") or ""),
                "source_unit_type": str(reference.get("unit_type") or ""),
                "source_field": str(reference.get("source_column") or ""),
                "source_text": str(reference.get("unit_text") or ""),
                "reason": (
                    "lexical_overlap"
                    if supported
                    else "no_supported_evidence_match"
                ),
                "evidence_role": "style" if supported else "unmatched",
                "similarity_score": round(best_score, 4) if supported else 0.0,
                "mapping_method": LEXICAL_EVIDENCE_MAPPING_VERSION,
                "needs_review": not supported,
                "retrieval_sources": list(
                    reference.get("retrieval_sources") or []
                ),
                "prompt_included": bool(
                    reference.get("prompt_included", False)
                ),
                "slot_match": False,
            }
        )
    return mappings


def _map_content_and_style_evidence(
    generated_text: str,
    *,
    input_text: str,
    evidence: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    input_references = [
        {
            "record_id": "",
            "unit_id": f"USER-INPUT-{index:03d}",
            "source_column": "user_input",
            "unit_text": span,
        }
        for index, span in enumerate(_input_spans(input_text), start=1)
    ]
    mappings: list[dict[str, Any]] = []
    sentence_matches = [
        match
        for match in _SENTENCE_RE.finditer(generated_text)
        if match.group(0).strip() and not _is_heading(match.group(0).strip())
    ]
    prompt_evidence = [
        reference
        for reference in evidence
        if bool(reference.get("prompt_included", False))
    ] or evidence
    for sentence_index, match in enumerate(sentence_matches, start=1):
        sentence = match.group(0).strip()
        generated_start = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
        generated_end = match.start() + len(match.group(0).rstrip())

        ranked_content = (
            []
            if _is_style_only_span(sentence)
            else _rank_references(sentence, input_references)
        )
        supported_content = [
            (reference, score)
            for reference, score in ranked_content
            if score >= 0.06
        ][:2]
        if supported_content:
            for content_index, (content, content_score) in enumerate(
                supported_content,
                start=1,
            ):
                mappings.append(
                    {
                        "mapping_id": f"MAP-{sentence_index:03d}-CONTENT-{content_index}",
                        "target_span": sentence,
                        "generated_start": generated_start,
                        "generated_end": generated_end,
                        "record_id": "",
                        "unit_id": str(content.get("unit_id") or ""),
                        "source_unit_type": "user_input",
                        "source_field": "user_input",
                        "source_text": str(content.get("unit_text") or ""),
                        "reason": "user_input_support",
                        "evidence_role": "content",
                        "similarity_score": round(content_score, 4),
                        "mapping_method": DUAL_EVIDENCE_MAPPING_VERSION,
                        "needs_review": False,
                        "retrieval_sources": [],
                        "prompt_included": False,
                        "slot_match": False,
                    }
                )
        elif not _is_style_only_span(sentence):
            mappings.append(
                {
                    "mapping_id": f"MAP-{sentence_index:03d}-CONTENT",
                    "target_span": sentence,
                    "generated_start": generated_start,
                    "generated_end": generated_end,
                    "record_id": "",
                    "unit_id": "",
                    "source_unit_type": "user_input",
                    "source_field": "user_input",
                    "source_text": "",
                    "reason": "no_user_input_support",
                    "evidence_role": "unmatched",
                    "similarity_score": 0.0,
                    "mapping_method": DUAL_EVIDENCE_MAPPING_VERSION,
                    "needs_review": True,
                    "retrieval_sources": [],
                    "prompt_included": False,
                    "slot_match": False,
                }
            )

        sentence_slots = _infer_sentence_style_slots(
            sentence,
            sentence_index=sentence_index,
            sentence_count=len(sentence_matches),
        )
        supported_style = _select_functional_style_references(
            sentence,
            prompt_evidence,
            sentence_slots=sentence_slots,
            limit=3,
        )
        if not supported_style:
            supported_style = [
                (reference, score, False)
                for reference, score in _select_style_references(
                    sentence,
                    prompt_evidence,
                    limit=2,
                    minimum_score=0.065,
                )
            ]
        if not supported_style:
            if _is_style_only_span(sentence):
                mappings.append(
                    {
                        "mapping_id": f"MAP-{sentence_index:03d}-STYLE",
                        "target_span": sentence,
                        "generated_start": generated_start,
                        "generated_end": generated_end,
                        "record_id": "",
                        "unit_id": "",
                        "source_unit_type": "",
                        "source_field": "",
                        "source_text": "",
                        "reason": "no_supported_evidence_match",
                        "evidence_role": "unmatched",
                        "similarity_score": 0.0,
                        "mapping_method": DUAL_EVIDENCE_MAPPING_VERSION,
                        "needs_review": True,
                        "retrieval_sources": [],
                        "prompt_included": False,
                        "slot_match": False,
                    }
                )
            continue
        for style_index, (
            style_reference,
            style_score,
            slot_match,
        ) in enumerate(
            supported_style,
            start=1,
        ):
            retrieval_sources = {
                str(source)
                for source in style_reference.get("retrieval_sources") or []
            }
            if slot_match and {"keyword", "semantic"}.issubset(retrieval_sources):
                reason = "hybrid_slot_style_support"
            elif slot_match and "semantic" in retrieval_sources:
                reason = "semantic_slot_style_support"
            elif slot_match:
                reason = "lexical_slot_style_support"
            elif {"keyword", "semantic"}.issubset(retrieval_sources):
                reason = "hybrid_style_support"
            elif "semantic" in retrieval_sources:
                reason = "semantic_style_support"
            else:
                reason = "lexical_style_support"
            mappings.append(
                {
                    "mapping_id": (
                        f"MAP-{sentence_index:03d}-STYLE-{style_index}"
                    ),
                    "target_span": sentence,
                    "generated_start": generated_start,
                    "generated_end": generated_end,
                    "record_id": str(style_reference.get("record_id") or ""),
                    "unit_id": str(style_reference.get("unit_id") or ""),
                    "source_unit_type": str(
                        style_reference.get("unit_type") or ""
                    ),
                    "source_field": str(
                        style_reference.get("source_column") or ""
                    ),
                    "source_text": str(style_reference.get("unit_text") or ""),
                    "reason": reason,
                    "evidence_role": "style",
                    "similarity_score": round(style_score, 4),
                    "mapping_method": DUAL_EVIDENCE_MAPPING_VERSION,
                    "needs_review": False,
                    "retrieval_sources": sorted(retrieval_sources),
                    "prompt_included": bool(
                        style_reference.get("prompt_included", False)
                    ),
                    "slot_match": slot_match,
                }
            )
    return mappings


def map_evidence(target_spans: list, evidence: list) -> list:
    generated_text = "。".join(str(span) for span in target_spans if str(span).strip())
    references = [
        {
            "record_id": item.get("record_id", ""),
            "unit_id": item.get("unit_id", ""),
            "source_column": item.get("source_field", item.get("source_column", "")),
            "unit_text": item.get("source_text", item.get("unit_text", "")),
        }
        for item in evidence
    ]
    return map_generated_text_to_evidence(generated_text, references)


def _support_score(generated_sentence: str, evidence_text: str) -> float:
    normalized_generated = _normalize_semantic_aliases(generated_sentence)
    normalized_evidence = _normalize_semantic_aliases(evidence_text)
    generated_tokens = _tokens(normalized_generated)
    evidence_tokens = _tokens(normalized_evidence)
    if not generated_tokens or not evidence_tokens:
        return 0.0
    overlap = generated_tokens & evidence_tokens
    token_score = len(overlap) / max(1, len(generated_tokens))
    generated_bigrams = _bigrams(normalized_generated)
    evidence_bigrams = _bigrams(normalized_evidence)
    bigram_score = (
        len(generated_bigrams & evidence_bigrams) / max(1, len(generated_bigrams))
        if generated_bigrams
        else 0.0
    )
    fact_score = _fact_support_score(generated_sentence, evidence_text)
    return min(
        1.0,
        (token_score * 0.35) + (bigram_score * 0.45) + (fact_score * 0.20),
    )


def _best_reference(
    sentence: str,
    references: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, float]:
    best_reference: Mapping[str, Any] | None = None
    best_score = 0.0
    for reference in references:
        score = _support_score(sentence, str(reference.get("unit_text") or ""))
        if score > best_score:
            best_score = score
            best_reference = reference
    return best_reference, best_score


def _rank_references(
    sentence: str,
    references: list[Mapping[str, Any]],
) -> list[tuple[Mapping[str, Any], float]]:
    return sorted(
        (
            (
                reference,
                _support_score(sentence, str(reference.get("unit_text") or "")),
            )
            for reference in references
        ),
        key=lambda item: (
            -item[1],
            str(item[0].get("unit_id") or ""),
        ),
    )


def _select_style_references(
    sentence: str,
    references: list[Mapping[str, Any]],
    *,
    limit: int,
    minimum_score: float,
) -> list[tuple[Mapping[str, Any], float]]:
    selected: list[tuple[Mapping[str, Any], float]] = []
    seen_units: set[str] = set()
    seen_records: set[str] = set()
    for reference, score in _rank_references(sentence, references):
        if score < minimum_score:
            continue
        unit_id = str(reference.get("unit_id") or "")
        record_id = str(reference.get("record_id") or "")
        if not unit_id or unit_id in seen_units:
            continue
        if selected and record_id and record_id in seen_records:
            continue
        selected.append((reference, score))
        seen_units.add(unit_id)
        if record_id:
            seen_records.add(record_id)
        if len(selected) >= limit:
            break
    return selected


def _select_functional_style_references(
    sentence: str,
    references: list[Mapping[str, Any]],
    *,
    sentence_slots: list[str],
    limit: int,
) -> list[tuple[Mapping[str, Any], float, bool]]:
    selected: list[tuple[Mapping[str, Any], float, bool]] = []
    seen_units: set[str] = set()
    for slot_type in sentence_slots:
        slot_references = [
            reference
            for reference in references
            if str(reference.get("unit_type") or "") == slot_type
        ]
        if not slot_references:
            continue
        ranked = _rank_references(sentence, slot_references)
        if not ranked:
            continue
        reference, lexical_score = ranked[0]
        unit_id = str(reference.get("unit_id") or "")
        if not unit_id or unit_id in seen_units:
            continue
        combined_score = min(1.0, 0.42 + (lexical_score * 0.58))
        selected.append((reference, combined_score, True))
        seen_units.add(unit_id)
        if len(selected) >= limit:
            break
    return selected


def _infer_sentence_style_slots(
    sentence: str,
    *,
    sentence_index: int,
    sentence_count: int,
) -> list[str]:
    clean = re.sub(r"\s+", "", sentence)
    slots: list[str] = []
    if (
        sentence_index == 1
        and len(clean) <= 24
        and any(marker in clean for marker in ("：", ":", "如晤", "尊前", "膝下", "收知"))
    ):
        slots.append("opening")

    facts = extract_facts(sentence)
    if facts.get("safety_terms") or any(
        marker in sentence for marker in _FUNCTIONAL_SLOT_MARKERS["safety"]
    ):
        slots.append("safety")
    if facts.get("amount_values") or facts.get("remittance_terms"):
        slots.append("remittance")
    if any(
        marker in sentence for marker in _FUNCTIONAL_SLOT_MARKERS["family_care"]
    ):
        slots.append("family_care")
    if any(
        marker in sentence for marker in _FUNCTIONAL_SLOT_MARKERS["instruction"]
    ):
        slots.append("instruction")

    if (
        sentence_index == sentence_count
        and len(clean) <= 24
        and (
            _is_style_only_span(sentence)
            or any(
                marker in clean
                for marker in (
                    "敬上",
                    "谨上",
                    "谨启",
                    "谨禀",
                    "叩上",
                    "泐",
                    "缄",
                    "顿",
                    "字",
                    "草",
                    "手书",
                    "启",
                )
            )
        )
    ):
        slots.append("closing")
    return list(dict.fromkeys(slots))


def _input_spans(text: str) -> list[str]:
    spans = [
        match.group(0).strip()
        for match in _INPUT_SPAN_RE.finditer(text)
        if match.group(0).strip()
    ]
    return spans or ([text.strip()] if text.strip() else [])


def _normalize_semantic_aliases(text: str) -> str:
    normalized = text
    for aliases, canonical in _SEMANTIC_ALIASES:
        for alias in aliases:
            normalized = normalized.replace(alias, canonical)
    return normalized


def _fact_support_score(generated_sentence: str, evidence_text: str) -> float:
    generated_facts = extract_facts(generated_sentence)
    evidence_facts = extract_facts(evidence_text)
    scores: list[float] = []
    for key in ("amount_values", "place_concepts"):
        generated_values = set(generated_facts.get(key) or [])
        if generated_values:
            evidence_values = set(evidence_facts.get(key) or [])
            scores.append(
                len(generated_values & evidence_values) / len(generated_values)
            )
    generated_kinship = set(generated_facts.get("kinship_terms") or [])
    if generated_kinship:
        evidence_kinship = set(evidence_facts.get("kinship_terms") or [])
        scores.append(1.0 if generated_kinship & evidence_kinship else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(text)
        if token not in {"生成", "解读", "草稿", "侨批", "内容", "这是"}
    }


def _bigrams(text: str) -> set[str]:
    compact = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)
    return {compact[index : index + 2] for index in range(max(0, len(compact) - 1))}


def _is_heading(sentence: str) -> bool:
    clean = sentence.strip()
    return clean.startswith("【") and clean.endswith("】")


def _is_style_only_span(sentence: str) -> bool:
    clean = re.sub(r"\s+", "", sentence)
    return len(clean) <= 14 and any(term in clean for term in _STYLE_ONLY_TERMS)
