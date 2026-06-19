from __future__ import annotations

import re
from typing import Any, Mapping


EVIDENCE_MAPPING_VERSION = "lexical-evidence-map-v1"
_SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{1,4}|[A-Za-z0-9_.-]+")


def map_generated_text_to_evidence(
    generated_text: str,
    evidence_references: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    evidence = [
        reference
        for reference in evidence_references
        if str(reference.get("unit_text") or "").strip()
    ]
    mappings: list[dict[str, Any]] = []
    for sentence_index, match in enumerate(_SENTENCE_RE.finditer(generated_text), start=1):
        sentence = match.group(0).strip()
        if not sentence or _is_heading(sentence):
            continue
        best_reference: Mapping[str, Any] | None = None
        best_score = 0.0
        for reference in evidence:
            score = _support_score(sentence, str(reference.get("unit_text") or ""))
            if score > best_score:
                best_score = score
                best_reference = reference

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
                "source_field": str(reference.get("source_column") or ""),
                "source_text": str(reference.get("unit_text") or ""),
                "reason": (
                    "lexical_overlap"
                    if supported
                    else "no_supported_evidence_match"
                ),
                "similarity_score": round(best_score, 4) if supported else 0.0,
                "mapping_method": EVIDENCE_MAPPING_VERSION,
                "needs_review": not supported,
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
    generated_tokens = _tokens(generated_sentence)
    evidence_tokens = _tokens(evidence_text)
    if not generated_tokens or not evidence_tokens:
        return 0.0
    overlap = generated_tokens & evidence_tokens
    token_score = len(overlap) / max(1, len(generated_tokens))
    generated_bigrams = _bigrams(generated_sentence)
    evidence_bigrams = _bigrams(evidence_text)
    bigram_score = (
        len(generated_bigrams & evidence_bigrams) / max(1, len(generated_bigrams))
        if generated_bigrams
        else 0.0
    )
    return min(1.0, (token_score * 0.45) + (bigram_score * 0.55))


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
