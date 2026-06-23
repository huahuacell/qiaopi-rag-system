from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable

try:
    import torch
    from torch import Tensor, nn
except ImportError:  # pragma: no cover - exercised only in minimal deployments.
    torch = None
    Tensor = Any
    nn = None


EMOTION_MODEL_VERSION = "qiaopi-emotion-pytorch-v1.0.0"
EMOTION_THRESHOLD = 0.52
LOW_CONFIDENCE_THRESHOLD = 0.62
_UNCERTAINTY_MARKERS = ("□", "�", "缺字", "待校", "未辨", "不清")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？!?；;])|\r?\n+")


@dataclass(frozen=True)
class EmotionDefinition:
    key: str
    label: str
    valence: str
    terms: tuple[tuple[str, float], ...]
    theme_hints: tuple[str, ...] = ()


EMOTION_DEFINITIONS: tuple[EmotionDefinition, ...] = (
    EmotionDefinition(
        key="longing_attachment",
        label="思念牵挂",
        valence="mixed",
        terms=(
            ("思念", 1.35),
            ("想念", 1.35),
            ("挂念", 1.2),
            ("惦念", 1.2),
            ("念你", 1.2),
            ("念及", 0.9),
            ("不忘", 0.85),
            ("未能忘怀", 1.15),
            ("盼归", 1.0),
            ("回归祖国", 0.75),
            ("见慈亲", 0.95),
            ("思故里", 1.2),
            ("乡思", 1.1),
            ("关山", 0.6),
            ("远隔", 0.7),
        ),
        theme_hints=("family_affection",),
    ),
    EmotionDefinition(
        key="reassurance_relief",
        label="平安欣慰",
        valence="positive",
        terms=(
            ("平安", 1.05),
            ("无恙", 1.15),
            ("安好", 1.0),
            ("康泰", 0.95),
            ("康健", 0.95),
            ("痊愈", 1.0),
            ("痊安", 1.0),
            ("清泰", 0.85),
            ("粗安", 0.8),
            ("甚慰", 1.15),
            ("为慰", 0.85),
            ("不胜喜", 1.25),
            ("喜乐", 1.05),
            ("放心", 0.9),
            ("勿念", 0.9),
            ("免挂念", 1.0),
            ("免介", 0.65),
            ("切勿介", 0.75),
        ),
        theme_hints=("safety", "health"),
    ),
    EmotionDefinition(
        key="care_instruction",
        label="关爱嘱托",
        valence="neutral",
        terms=(
            ("珍重", 1.05),
            ("保重", 1.05),
            ("照顾", 0.9),
            ("切勿过劳", 1.15),
            ("勿过劳", 1.05),
            ("祈为", 0.5),
            ("望祈", 0.55),
            ("嘱令", 0.8),
            ("教训", 0.7),
            ("教养", 0.7),
            ("勤作", 0.65),
            ("和睦", 0.75),
            ("不可忤逆", 0.85),
            ("勿负", 0.65),
            ("为要", 0.55),
            ("所至盼", 0.75),
            ("善自", 0.65),
            ("调理", 0.65),
        ),
        theme_hints=("instruction", "health", "study"),
    ),
    EmotionDefinition(
        key="worry_pressure",
        label="忧虑压力",
        valence="negative",
        terms=(
            ("担忧", 1.2),
            ("忧虑", 1.2),
            ("忧心", 1.15),
            ("挂怀", 0.85),
            ("病情", 0.9),
            ("病苦", 1.05),
            ("艰难", 0.95),
            ("困难", 0.9),
            ("甚苦", 1.05),
            ("难得", 0.7),
            ("无余资", 1.0),
            ("无银", 0.85),
            ("债", 0.8),
            ("欠", 0.65),
            ("衰薄", 1.0),
            ("不能回归", 0.95),
            ("无厝可居", 1.05),
            ("劳苦", 0.85),
            ("操劳", 0.75),
            ("不晓", 0.55),
            ("耻笑", 0.75),
            ("误精神", 0.65),
        ),
        theme_hints=("debt", "health", "work", "home_building"),
    ),
    EmotionDefinition(
        key="grief_sorrow",
        label="悲伤哀痛",
        valence="negative",
        terms=(
            ("悲痛", 1.4),
            ("哀痛", 1.4),
            ("伤心", 1.25),
            ("痛心", 1.25),
            ("不幸", 1.0),
            ("去世", 1.25),
            ("逝世", 1.25),
            ("亡故", 1.3),
            ("病故", 1.3),
            ("孝服", 1.05),
            ("丧事", 1.15),
            ("吊唁", 1.1),
            ("节哀", 1.2),
            ("罪实甚", 0.9),
            ("愧", 0.75),
        ),
        theme_hints=("funeral",),
    ),
    EmotionDefinition(
        key="gratitude_blessing",
        label="感激祝愿",
        valence="positive",
        terms=(
            ("感激", 1.2),
            ("感谢", 1.15),
            ("荷蒙", 0.95),
            ("承蒙", 0.85),
            ("蒙神天", 0.9),
            ("神天之佑", 1.0),
            ("天庇", 0.9),
            ("祝", 0.65),
            ("福安", 0.8),
            ("金安", 0.75),
            ("近安", 0.65),
            ("佳安", 0.65),
            ("顺颂", 0.65),
            ("敬请", 0.5),
            ("跪请", 0.55),
            ("清吉", 0.75),
            ("遂心", 0.7),
            ("胜意", 0.7),
        ),
    ),
    EmotionDefinition(
        key="practical_neutral",
        label="事务陈述",
        valence="neutral",
        terms=(
            ("查收", 0.85),
            ("家用", 0.8),
            ("寄去", 0.65),
            ("奉上", 0.65),
            ("付去", 0.65),
            ("银", 0.35),
            ("元", 0.25),
            ("生意", 0.65),
            ("田园", 0.55),
            ("租赁", 0.65),
            ("回信", 0.55),
            ("示知", 0.55),
            ("船便", 0.5),
            ("轮便", 0.5),
            ("此告", 0.45),
            ("余言", 0.4),
        ),
        theme_hints=("remittance", "work", "home_building"),
    ),
)

_EMOTION_INDEX = {
    definition.key: index for index, definition in enumerate(EMOTION_DEFINITIONS)
}
_POSITIVE_KEYS = {"reassurance_relief", "gratitude_blessing"}
_NEGATIVE_KEYS = {"worry_pressure", "grief_sorrow"}


if nn is not None:

    class DomainEmotionHead(nn.Module):
        """Small deterministic PyTorch head over interpretable domain features."""

        def __init__(self) -> None:
            super().__init__()
            label_count = len(EMOTION_DEFINITIONS)
            weights = torch.eye(label_count, dtype=torch.float32) * 3.15
            bias = torch.full((label_count,), -1.72, dtype=torch.float32)

            # A small amount of domain co-occurrence improves mixed-letter recall
            # without allowing one label to dominate another.
            weights[_EMOTION_INDEX["longing_attachment"], _EMOTION_INDEX["worry_pressure"]] = 0.18
            weights[_EMOTION_INDEX["care_instruction"], _EMOTION_INDEX["worry_pressure"]] = 0.12
            weights[_EMOTION_INDEX["reassurance_relief"], _EMOTION_INDEX["gratitude_blessing"]] = 0.10
            weights[_EMOTION_INDEX["practical_neutral"], _EMOTION_INDEX["care_instruction"]] = 0.08

            self.register_buffer("weights", weights)
            self.register_buffer("bias", bias)

        def forward(self, features: Tensor) -> Tensor:
            return torch.sigmoid(features @ self.weights.T + self.bias)


def split_qiaopi_segments(text: str) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", str(text or "")).strip()
    if not normalized:
        return []

    segments: list[str] = []
    for raw_segment in _SENTENCE_SPLIT_PATTERN.split(normalized):
        segment = raw_segment.strip(" \r\n\t")
        if not segment:
            continue
        if len(segment) <= 180:
            segments.append(segment)
            continue
        # Long OCR paragraphs are split again at commas while retaining readable evidence.
        chunks = re.split(r"(?<=[，,])", segment)
        buffer = ""
        for chunk in chunks:
            if len(buffer) + len(chunk) <= 180:
                buffer += chunk
            else:
                if buffer.strip():
                    segments.append(buffer.strip())
                buffer = chunk
        if buffer.strip():
            segments.append(buffer.strip())
    return segments


def _matched_terms(
    segment: str,
    definition: EmotionDefinition,
) -> tuple[list[str], float]:
    matches: list[str] = []
    raw_score = 0.0
    for term, weight in definition.terms:
        term_matches = list(re.finditer(re.escape(term), segment))
        if not term_matches:
            continue
        accepted_occurrences = 0
        for term_match in term_matches:
            prefix = segment[max(0, term_match.start() - 4) : term_match.start()]
            if (
                definition.key in {"longing_attachment", "worry_pressure"}
                and re.search(r"(?:切勿|勿|莫|免|无须|毋须|不必)$", prefix)
            ):
                continue
            accepted_occurrences += 1
        if accepted_occurrences:
            matches.append(term)
            raw_score += weight * min(accepted_occurrences, 2)
    return matches, raw_score


def _feature_vector(
    segment: str,
    theme_tags: Iterable[str],
) -> tuple[list[float], dict[str, list[str]]]:
    theme_set = {str(tag).strip() for tag in theme_tags if str(tag).strip()}
    feature_values: list[float] = []
    matched_by_label: dict[str, list[str]] = {}
    any_affective_match = False

    for definition in EMOTION_DEFINITIONS:
        matches, raw_score = _matched_terms(segment, definition)
        if definition.key != "practical_neutral" and matches:
            any_affective_match = True
        if matches:
            matched_by_label[definition.key] = matches
        if definition.theme_hints and theme_set.intersection(definition.theme_hints):
            raw_score += 0.12

        length_penalty = 1.0 + max(len(segment) - 48, 0) / 320
        normalized_score = math.tanh(raw_score / length_penalty)
        feature_values.append(normalized_score)

    practical_index = _EMOTION_INDEX["practical_neutral"]
    if not any_affective_match and len(segment) >= 8:
        feature_values[practical_index] = max(feature_values[practical_index], 0.62)
    return feature_values, matched_by_label


def _python_sigmoid_scores(feature_values: list[float]) -> list[float]:
    scores: list[float] = []
    for index, feature in enumerate(feature_values):
        logit = feature * 3.15 - 1.72
        if index == _EMOTION_INDEX["longing_attachment"]:
            logit += feature_values[_EMOTION_INDEX["worry_pressure"]] * 0.18
        elif index == _EMOTION_INDEX["care_instruction"]:
            logit += feature_values[_EMOTION_INDEX["worry_pressure"]] * 0.12
        elif index == _EMOTION_INDEX["reassurance_relief"]:
            logit += feature_values[_EMOTION_INDEX["gratitude_blessing"]] * 0.10
        elif index == _EMOTION_INDEX["practical_neutral"]:
            logit += feature_values[_EMOTION_INDEX["care_instruction"]] * 0.08
        scores.append(1.0 / (1.0 + math.exp(-logit)))
    return scores


def _predict_scores(feature_values: list[float]) -> tuple[list[float], str, bool]:
    if torch is None or nn is None:
        return _python_sigmoid_scores(feature_values), "python_compatible_fallback", False

    model = DomainEmotionHead()
    model.eval()
    with torch.inference_mode():
        features = torch.tensor([feature_values], dtype=torch.float32)
        scores = model(features)[0].tolist()
    return [float(score) for score in scores], "pytorch", True


def _segment_valence(predictions: list[dict[str, Any]]) -> str:
    keys = {prediction["key"] for prediction in predictions}
    has_positive = bool(keys.intersection(_POSITIVE_KEYS))
    has_negative = bool(keys.intersection(_NEGATIVE_KEYS))
    if has_positive and has_negative:
        return "mixed"
    if has_negative:
        return "negative"
    if has_positive:
        return "positive"
    if "longing_attachment" in keys:
        return "mixed"
    return "neutral"


def classify_segment(
    segment: str,
    *,
    theme_tags: Iterable[str] = (),
) -> dict[str, Any]:
    feature_values, matched_by_label = _feature_vector(segment, theme_tags)
    scores, engine, torch_available = _predict_scores(feature_values)

    predictions: list[dict[str, Any]] = []
    for definition, score in zip(EMOTION_DEFINITIONS, scores):
        if score < EMOTION_THRESHOLD:
            continue
        predictions.append(
            {
                "key": definition.key,
                "label": definition.label,
                "confidence": round(score, 4),
                "trigger_terms": matched_by_label.get(definition.key, []),
                "valence": definition.valence,
            }
        )

    if not predictions:
        practical_index = _EMOTION_INDEX["practical_neutral"]
        predictions = [
            {
                "key": "practical_neutral",
                "label": EMOTION_DEFINITIONS[practical_index].label,
                "confidence": round(max(scores[practical_index], 0.5), 4),
                "trigger_terms": [],
                "valence": "neutral",
            }
        ]

    predictions.sort(key=lambda item: (-item["confidence"], item["key"]))
    maximum_confidence = predictions[0]["confidence"]
    uncertainty_detected = any(marker in segment for marker in _UNCERTAINTY_MARKERS)
    return {
        "text": segment,
        "predictions": predictions,
        "valence": _segment_valence(predictions),
        "maximum_confidence": maximum_confidence,
        "needs_review": uncertainty_detected
        or maximum_confidence < LOW_CONFIDENCE_THRESHOLD,
        "uncertainty_detected": uncertainty_detected,
        "engine": engine,
        "torch_available": torch_available,
    }


def classify_record(record: dict[str, Any]) -> dict[str, Any]:
    body_text = str(record.get("body_core") or record.get("body_clean") or "").strip()
    theme_tags = [
        tag for tag in str(record.get("theme_tags") or "").split(";") if tag
    ]
    segment_results = [
        classify_segment(segment, theme_tags=theme_tags)
        for segment in split_qiaopi_segments(body_text)
    ]

    label_segments: dict[str, list[dict[str, Any]]] = {
        definition.key: [] for definition in EMOTION_DEFINITIONS
    }
    for segment_result in segment_results:
        for prediction in segment_result["predictions"]:
            label_segments[prediction["key"]].append(
                {
                    "text": segment_result["text"],
                    "confidence": prediction["confidence"],
                    "trigger_terms": prediction["trigger_terms"],
                    "valence": segment_result["valence"],
                    "needs_review": segment_result["needs_review"],
                }
            )

    labels: list[dict[str, Any]] = []
    for definition in EMOTION_DEFINITIONS:
        evidence = label_segments[definition.key]
        if not evidence:
            continue
        confidences = [float(item["confidence"]) for item in evidence]
        record_confidence = max(confidences) * 0.72 + (
            sum(confidences) / len(confidences)
        ) * 0.28
        labels.append(
            {
                "key": definition.key,
                "label": definition.label,
                "confidence": round(min(record_confidence, 0.9999), 4),
                "segment_count": len(evidence),
                "evidence": sorted(
                    evidence,
                    key=lambda item: (-item["confidence"], len(item["text"])),
                ),
            }
        )
    labels.sort(key=lambda item: (-item["confidence"], item["key"]))

    label_confidence_by_key = {
        label["key"]: float(label["confidence"]) for label in labels
    }
    positive_score = max(
        (label_confidence_by_key.get(key, 0.0) for key in _POSITIVE_KEYS),
        default=0.0,
    )
    negative_score = max(
        (label_confidence_by_key.get(key, 0.0) for key in _NEGATIVE_KEYS),
        default=0.0,
    )
    longing_score = label_confidence_by_key.get("longing_attachment", 0.0)
    if positive_score >= EMOTION_THRESHOLD and negative_score >= EMOTION_THRESHOLD:
        dominant_valence = "mixed"
    elif negative_score >= EMOTION_THRESHOLD:
        dominant_valence = "negative"
    elif longing_score >= EMOTION_THRESHOLD:
        dominant_valence = "mixed"
    elif positive_score >= EMOTION_THRESHOLD:
        dominant_valence = "positive"
    else:
        dominant_valence = "neutral"

    valence_counts: dict[str, int] = {
        key: sum(result["valence"] == key for result in segment_results)
        for key in ("positive", "neutral", "negative", "mixed")
    }

    uncertainty_segment_count = sum(
        result["uncertainty_detected"] for result in segment_results
    )
    dominant_label_confidence = float(labels[0]["confidence"]) if labels else 0.0
    low_confidence = (
        not segment_results
        or dominant_label_confidence < 0.56
        or uncertainty_segment_count / max(len(segment_results), 1) > 0.25
    )
    return {
        "record_id": str(record.get("record_id") or ""),
        "year": str(record.get("year_normalized") or ""),
        "labels": labels,
        "dominant_emotion_key": labels[0]["key"] if labels else "practical_neutral",
        "dominant_emotion_label": labels[0]["label"] if labels else "事务陈述",
        "dominant_valence": dominant_valence,
        "valence_counts": valence_counts,
        "segment_count": len(segment_results),
        "low_confidence": low_confidence,
        "engine": segment_results[0]["engine"] if segment_results else "pytorch",
        "torch_available": (
            segment_results[0]["torch_available"] if segment_results else torch is not None
        ),
    }
