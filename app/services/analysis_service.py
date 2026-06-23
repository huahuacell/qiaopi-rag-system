from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations
from pathlib import Path
from threading import Lock
from typing import Any

from app.analysis.emotion_classifier import (
    EMOTION_DEFINITIONS,
    EMOTION_MODEL_VERSION,
    EMOTION_THRESHOLD,
    classify_record,
)
from app.database.repository import (
    fetch_dashboard_stats,
    fetch_emotion_analysis_records,
)
from app.settings import QIAOPI_DB_PATH


_CACHE_LOCK = Lock()
_CACHE_KEY: tuple[int, int] | None = None
_CACHE_VALUE: dict[str, Any] | None = None
_VALENCE_LABELS = {
    "positive": "积极安慰",
    "neutral": "中性事务",
    "negative": "忧虑哀伤",
    "mixed": "复合情感",
}


def _database_fingerprint(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return (0, 0)
    return (stat.st_mtime_ns, stat.st_size)


def _round_ratio(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(value / total, 4)


def _period_for_year(year_text: str) -> str | None:
    if not year_text.isdigit():
        return None
    year = int(year_text)
    if not 1800 <= year <= 2100:
        return None
    period_start = year // 5 * 5
    return f"{period_start}—{period_start + 4}"


def _build_empty_payload(torch_available: bool) -> dict[str, Any]:
    return {
        "total_records": 0,
        "analyzed_records": 0,
        "analyzed_segments": 0,
        "multi_label_records": 0,
        "mixed_valence_records": 0,
        "low_confidence_records": 0,
        "dominant_emotion_key": "practical_neutral",
        "dominant_emotion_label": "事务陈述",
        "label_distribution": [],
        "valence_distribution": [],
        "cooccurrence": [],
        "time_trend": [],
        "evidence_examples": [],
        "model": {
            "engine": "pytorch" if torch_available else "python_compatible_fallback",
            "model_version": EMOTION_MODEL_VERSION,
            "torch_available": torch_available,
            "device": "cpu",
            "classifier_type": "可解释领域特征 + PyTorch 多标签 Sigmoid 分类头",
            "label_count": len(EMOTION_DEFINITIONS),
            "threshold": EMOTION_THRESHOLD,
            "calibrated": False,
            "methodology": "句段级多标签分类，随后聚合到信件和馆藏层级。",
            "limitations": "当前为小样本阶段的可解释基线，不宣称等同于人工标注金标准。",
        },
        "warnings": ["没有可分析的全文记录。"],
    }


def _compute_emotion_analysis() -> dict[str, Any]:
    records = fetch_emotion_analysis_records()
    if not records:
        return _build_empty_payload(torch_available=False)

    total_text_records = fetch_dashboard_stats()["total_text_records"]
    classified_records = [classify_record(record) for record in records]
    analyzed_records = len(classified_records)
    label_record_counts: Counter[str] = Counter()
    label_segment_counts: Counter[str] = Counter()
    label_confidences: dict[str, list[float]] = defaultdict(list)
    valence_counts: Counter[str] = Counter()
    cooccurrence_counts: Counter[tuple[str, str]] = Counter()
    evidence_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    period_records: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in classified_records:
        record_keys = [label["key"] for label in record["labels"]]
        for label in record["labels"]:
            label_record_counts[label["key"]] += 1
            label_segment_counts[label["key"]] += int(label["segment_count"])
            label_confidences[label["key"]].append(float(label["confidence"]))
            for evidence in label["evidence"][:2]:
                evidence_candidates[label["key"]].append(
                    {
                        "record_id": record["record_id"],
                        "year": record["year"],
                        "emotion_key": label["key"],
                        "emotion_label": label["label"],
                        "text": evidence["text"],
                        "trigger_terms": evidence["trigger_terms"],
                        "confidence": evidence["confidence"],
                        "valence": evidence["valence"],
                        "needs_review": evidence["needs_review"],
                    }
                )
        for left_key, right_key in combinations(sorted(set(record_keys)), 2):
            cooccurrence_counts[(left_key, right_key)] += 1
        valence_counts[record["dominant_valence"]] += 1
        period = _period_for_year(record["year"])
        if period:
            period_records[period].append(record)

    definitions_by_key = {
        definition.key: definition for definition in EMOTION_DEFINITIONS
    }
    label_distribution: list[dict[str, Any]] = []
    for definition in EMOTION_DEFINITIONS:
        count = label_record_counts[definition.key]
        confidences = label_confidences[definition.key]
        label_distribution.append(
            {
                "key": definition.key,
                "label": definition.label,
                "record_count": count,
                "segment_count": label_segment_counts[definition.key],
                "ratio": _round_ratio(count, analyzed_records),
                "average_confidence": round(
                    sum(confidences) / len(confidences), 4
                )
                if confidences
                else 0.0,
                "valence": definition.valence,
            }
        )
    label_distribution.sort(
        key=lambda item: (-item["record_count"], item["key"])
    )

    valence_distribution = [
        {
            "key": key,
            "label": label,
            "record_count": valence_counts[key],
            "ratio": _round_ratio(valence_counts[key], analyzed_records),
        }
        for key, label in _VALENCE_LABELS.items()
    ]

    cooccurrence = [
        {
            "left_key": left_key,
            "left_label": definitions_by_key[left_key].label,
            "right_key": right_key,
            "right_label": definitions_by_key[right_key].label,
            "record_count": count,
            "ratio": _round_ratio(count, analyzed_records),
        }
        for (left_key, right_key), count in cooccurrence_counts.most_common(12)
        if count > 0
    ]

    time_trend: list[dict[str, Any]] = []
    for period, period_items in sorted(period_records.items()):
        if len(period_items) < 2:
            continue
        period_label_counts = Counter(
            label["key"]
            for record in period_items
            for label in record["labels"]
            if label["key"] != "practical_neutral"
        )
        if not period_label_counts:
            period_label_counts["practical_neutral"] = len(period_items)
        dominant_key, _ = period_label_counts.most_common(1)[0]
        time_trend.append(
            {
                "period": period,
                "record_count": len(period_items),
                "dominant_emotion_key": dominant_key,
                "dominant_emotion_label": definitions_by_key[dominant_key].label,
                "distribution": {
                    definition.key: _round_ratio(
                        period_label_counts[definition.key],
                        len(period_items),
                    )
                    for definition in EMOTION_DEFINITIONS
                },
            }
        )

    evidence_examples: list[dict[str, Any]] = []
    for definition in EMOTION_DEFINITIONS:
        candidates = sorted(
            evidence_candidates[definition.key],
            key=lambda item: (
                item["needs_review"],
                -item["confidence"],
                len(item["text"]),
                item["record_id"],
            ),
        )
        evidence_examples.extend(candidates[:6])

    affective_distribution = [
        item for item in label_distribution if item["key"] != "practical_neutral"
    ]
    dominant_emotion = (
        affective_distribution[0] if affective_distribution else label_distribution[0]
    )
    torch_available = all(record["torch_available"] for record in classified_records)
    engine = "pytorch" if torch_available else "python_compatible_fallback"
    warnings = [
        "本结果是馆藏探索性统计，不能替代人工史料解读或监督学习金标准。",
        "一封侨批可同时包含多种情感，因此各情感占比之和可能超过 100%。",
    ]
    if not torch_available:
        warnings.append(
            "当前环境未安装 PyTorch，已使用数学等价兼容路径；安装语义依赖后可恢复 PyTorch 执行。"
        )

    return {
        "total_records": total_text_records,
        "analyzed_records": analyzed_records,
        "analyzed_segments": sum(
            record["segment_count"] for record in classified_records
        ),
        "multi_label_records": sum(
            len(record["labels"]) > 1 for record in classified_records
        ),
        "mixed_valence_records": valence_counts["mixed"],
        "low_confidence_records": sum(
            record["low_confidence"] for record in classified_records
        ),
        "dominant_emotion_key": dominant_emotion["key"],
        "dominant_emotion_label": dominant_emotion["label"],
        "label_distribution": label_distribution,
        "valence_distribution": valence_distribution,
        "cooccurrence": cooccurrence,
        "time_trend": time_trend,
        "evidence_examples": evidence_examples,
        "model": {
            "engine": engine,
            "model_version": EMOTION_MODEL_VERSION,
            "torch_available": torch_available,
            "device": "cpu",
            "classifier_type": "可解释领域特征 + PyTorch 多标签 Sigmoid 分类头",
            "label_count": len(EMOTION_DEFINITIONS),
            "threshold": EMOTION_THRESHOLD,
            "calibrated": False,
            "methodology": "按标点切分句段，保留触发词和原文片段，执行多标签分类后聚合到信件、年代与馆藏层级。",
            "limitations": "当前 213 条记录中有 202 封可用全文，尚未形成充分人工标注集；置信度用于排序与复核，不应解释为统计学概率。",
        },
        "warnings": warnings,
    }


def get_emotion_analysis(*, force_refresh: bool = False) -> dict[str, Any]:
    global _CACHE_KEY, _CACHE_VALUE

    fingerprint = _database_fingerprint(QIAOPI_DB_PATH)
    with _CACHE_LOCK:
        if (
            not force_refresh
            and _CACHE_KEY == fingerprint
            and _CACHE_VALUE is not None
        ):
            return deepcopy(_CACHE_VALUE)

    payload = _compute_emotion_analysis()
    with _CACHE_LOCK:
        _CACHE_KEY = fingerprint
        _CACHE_VALUE = payload
    return deepcopy(payload)
