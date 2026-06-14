from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping

from app.metadata.metadata_parser import normalize_name, normalize_title


AUTO_LINK_THRESHOLD = 0.92
CANDIDATE_LINK_THRESHOLD = 0.75
KINSHIP_MATCH_GROUPS: tuple[tuple[str, ...], ...] = (
    ("母亲", "慈亲", "家母", "家慈", "慈母"),
    ("父亲", "严亲", "家父", "家严", "严父"),
    ("父母", "双亲", "严慈"),
    ("妻子", "妻", "吾妻", "我妻", "荆妻"),
    ("儿子", "儿", "吾儿", "我儿"),
    ("祖父", "祖父"),
    ("祖母", "祖母"),
    ("嫂", "嫂", "大嫂"),
)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _flag(value: Any) -> int:
    return 1 if str(value).strip().lower() in {"1", "true", "yes"} else 0


def _compact_title(value: str) -> str:
    text = normalize_title(value)
    text = re.sub(r"(侨批|广东|民国|年|月|日|号|初|廿|念|十|拾|一|二|三|四|五|六|七|八|九|零|〇|\d)", "", text)
    return text


def _title_similarity(record_title: str, metadata_title: str) -> float:
    record_compact = _compact_title(record_title)
    metadata_compact = _compact_title(metadata_title)
    if not record_compact or not metadata_compact:
        return 0.0
    if metadata_compact in record_compact or record_compact in metadata_compact:
        return 0.98
    sequence_score = SequenceMatcher(None, record_compact, metadata_compact).ratio()
    record_chars = set(record_compact)
    metadata_chars = set(metadata_compact)
    overlap_score = len(record_chars & metadata_chars) / max(len(metadata_chars), 1)
    return round(max(sequence_score, overlap_score * 0.92), 4)


def _field_match(left: str, right: str) -> bool:
    left_raw = _text(left)
    right_raw = _text(right)
    for aliases in KINSHIP_MATCH_GROUPS:
        if any(alias in left_raw for alias in aliases) and any(alias in right_raw for alias in aliases):
            return True
    left_clean = normalize_name(left)
    right_clean = normalize_name(right)
    if not left_clean or not right_clean:
        return False
    return left_clean == right_clean or left_clean in right_clean or right_clean in left_clean


def _place_match(record: Mapping[str, Any], metadata: Mapping[str, Any]) -> bool:
    record_places = _text(record.get("place_mentions_normalized"))
    metadata_places = "；".join(
        [
            _text(metadata.get("origin_place")),
            _text(metadata.get("destination_place")),
            _text(metadata.get("place_mentions")),
            _text(metadata.get("country_or_region")),
        ]
    )
    if not record_places or not metadata_places:
        return False
    for place in record_places.split("；"):
        clean_place = place.strip()
        if clean_place and clean_place in metadata_places:
            return True
    return False


def _matched_fields(record: Mapping[str, Any], metadata: Mapping[str, Any], title_similarity: float) -> dict[str, Any]:
    sender_match = _field_match(_text(record.get("sender_name_clean")), _text(metadata.get("sender_name_clean")))
    recipient_match = _field_match(
        _text(record.get("recipient_name_clean")),
        "；".join(
            [
                _text(metadata.get("recipient_name_clean")),
                _text(metadata.get("recipient_raw")),
                _text(metadata.get("kinship_terms")),
            ]
        ),
    )
    year_match = bool(
        _text(record.get("year_normalized"))
        and _text(record.get("year_normalized")) == _text(metadata.get("year_normalized"))
    )
    place_match = _place_match(record, metadata)
    remittance_match = _flag(record.get("has_remittance")) == _flag(metadata.get("has_remittance"))
    return {
        "title_similarity": title_similarity,
        "sender_match": sender_match,
        "recipient_match": recipient_match,
        "year_match": year_match,
        "place_match": place_match,
        "remittance_match": remittance_match,
    }


def _confidence_from_matches(matches: Mapping[str, Any]) -> float:
    title_similarity = float(matches["title_similarity"])
    score = title_similarity * 0.50
    score += 0.18 if matches["sender_match"] else 0.0
    score += 0.14 if matches["recipient_match"] else 0.0
    score += 0.08 if matches["year_match"] else 0.0
    score += 0.06 if matches["place_match"] else 0.0
    score += 0.04 if matches["remittance_match"] else 0.0
    if title_similarity >= 0.96 and matches["sender_match"]:
        score = max(score, 0.93)
    if (
        matches["sender_match"]
        and matches["recipient_match"]
        and matches["year_match"]
        and title_similarity >= 0.50
    ):
        score = max(score, 0.92)
    if (
        matches["sender_match"]
        and matches["recipient_match"]
        and matches["place_match"]
        and title_similarity >= 0.70
    ):
        score = max(score, 0.76)
    return round(min(score, 0.99), 4)


def _method_for_matches(matches: Mapping[str, Any], confidence: float) -> str:
    if confidence >= 0.97:
        return "normalized_title"
    if matches["sender_match"] and matches["recipient_match"] and matches["year_match"]:
        return "field_composite"
    if matches["title_similarity"] >= 0.75:
        return "fuzzy_title"
    return "field_candidate"


def _index_metadata_records(metadata_records: Iterable[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    index: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for metadata in metadata_records:
        keys = {
            normalize_name(_text(metadata.get("sender_name_clean"))),
            normalize_name(_text(metadata.get("sender_raw"))),
            normalize_name(_text(metadata.get("recipient_name_clean"))),
        }
        for key in keys:
            if key and len(key) >= 2:
                index[key].append(metadata)
    return index


def _candidate_records(
    record: Mapping[str, Any],
    index: Mapping[str, list[Mapping[str, Any]]],
    metadata_records: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    keys = [
        normalize_name(_text(record.get("sender_name_clean"))),
        normalize_name(_text(record.get("sender"))),
        normalize_name(_text(record.get("recipient_name_clean"))),
    ]
    candidates: dict[str, Mapping[str, Any]] = {}
    for key in keys:
        if key and len(key) >= 2:
            for metadata in index.get(key, []):
                candidates[_text(metadata.get("metadata_id"))] = metadata
    if candidates:
        return list(candidates.values())

    record_year = _text(record.get("year_normalized"))
    if record_year:
        year_candidates = [
            metadata for metadata in metadata_records if _text(metadata.get("year_normalized")) == record_year
        ]
        return year_candidates[:500]
    return metadata_records[:500]


def build_metadata_text_links(
    text_records: list[Mapping[str, Any]],
    metadata_records: list[Mapping[str, Any]],
) -> dict[str, Any]:
    metadata_index = _index_metadata_records(metadata_records)
    auto_links: list[dict[str, Any]] = []
    candidate_links: list[dict[str, Any]] = []
    used_metadata_ids: set[str] = set()
    method_counts: Counter[str] = Counter()

    for record in text_records:
        scored: list[dict[str, Any]] = []
        for metadata in _candidate_records(record, metadata_index, metadata_records):
            title_similarity = _title_similarity(
                _text(record.get("title_reference")),
                _text(metadata.get("title_clean")),
            )
            matches = _matched_fields(record, metadata, title_similarity)
            confidence = _confidence_from_matches(matches)
            if confidence < CANDIDATE_LINK_THRESHOLD:
                continue
            method = _method_for_matches(matches, confidence)
            scored.append(
                {
                    "record_id": _text(record.get("record_id")),
                    "metadata_id": _text(metadata.get("metadata_id")),
                    "confidence": confidence,
                    "title_similarity": title_similarity,
                    "method": method,
                    "matched_fields": matches,
                }
            )
        scored.sort(key=lambda item: (-item["confidence"], -item["title_similarity"], item["metadata_id"]))
        if not scored:
            continue

        best = scored[0]
        record_id = best["record_id"]
        if best["confidence"] >= AUTO_LINK_THRESHOLD and best["metadata_id"] not in used_metadata_ids:
            used_metadata_ids.add(best["metadata_id"])
            method_counts[best["method"]] += 1
            auto_links.append(
                {
                    "link_id": f"LINK-{record_id}-{best['metadata_id']}",
                    "record_id": record_id,
                    "metadata_id": best["metadata_id"],
                    "link_method": best["method"],
                    "link_confidence": best["confidence"],
                    "title_similarity": best["title_similarity"],
                    "matched_fields_json": json.dumps(best["matched_fields"], ensure_ascii=False, sort_keys=True),
                }
            )
            extra_candidates = scored[1:4]
        else:
            extra_candidates = scored[:4]

        for rank, candidate in enumerate(extra_candidates, start=1):
            if candidate["metadata_id"] in used_metadata_ids:
                reason = "metadata_already_auto_linked"
            elif candidate["confidence"] >= AUTO_LINK_THRESHOLD:
                reason = "additional_high_confidence_candidate"
            else:
                reason = "manual_review_candidate"
            candidate_links.append(
                {
                    "candidate_id": f"CAND-{record_id}-{candidate['metadata_id']}-{rank}",
                    "record_id": record_id,
                    "metadata_id": candidate["metadata_id"],
                    "candidate_method": candidate["method"],
                    "candidate_confidence": candidate["confidence"],
                    "title_similarity": candidate["title_similarity"],
                    "matched_fields_json": json.dumps(
                        candidate["matched_fields"], ensure_ascii=False, sort_keys=True
                    ),
                    "reason": reason,
                }
            )

    return {
        "auto_links": auto_links,
        "candidate_links": candidate_links,
        "method_counts": dict(method_counts),
    }
