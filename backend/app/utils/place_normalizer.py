from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


_PLACE_SEPARATOR_RE = re.compile(r"[;；,，、\n\r\t]+")

_ORIGIN_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("越南", ("越南", "安南")),
    ("新加坡", ("新加坡", "星洲", "叻埠", "石叻", "叻坡", "叻")),
    ("泰国", ("泰国", "暹罗")),
    ("中国香港", ("中国香港", "香港")),
)

_GUANGDONG_ALIASES = (
    "广东侨乡",
    "广东",
    "潮安",
    "潮汕",
    "澄海",
    "饶平",
    "汕头",
    "揭阳",
    "普宁",
    "大埔",
    "梅县",
)


@dataclass(frozen=True)
class NormalizedPlaceFields:
    origin_place: str = ""
    destination_place: str = ""
    country_or_region: str = ""

    def as_db_fields(self) -> dict[str, str]:
        return {
            "origin_place": self.origin_place,
            "destination_place": self.destination_place,
            "country_or_region": self.country_or_region,
        }


def normalize_qiaopi_place_fields(row: Mapping[str, Any]) -> NormalizedPlaceFields:
    raw_json = _raw_json_mapping(row.get("raw_json"))
    place_mentions = _split_places(
        _first_text(row, raw_json, "place_mentions_normalized", "place_mentions")
    )

    origin = _normalize_origin(
        _first_text(row, raw_json, "origin_place", "overseas_place")
    )
    destination = _normalize_destination(
        _first_text(row, raw_json, "destination_place", "hometown_place")
    )
    country_or_region = _first_text(row, raw_json, "country_or_region")

    if not origin:
        origin = _infer_origin(place_mentions)
    if not destination:
        destination = _infer_destination(place_mentions)
    if not country_or_region:
        country_or_region = _infer_country_or_region(
            origin=origin,
            destination=destination,
            place_mentions=place_mentions,
        )

    return NormalizedPlaceFields(
        origin_place=origin,
        destination_place=destination,
        country_or_region=country_or_region,
    )


def _raw_json_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    text = _text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, Mapping) else {}


def _first_text(
    row: Mapping[str, Any],
    raw_json: Mapping[str, Any],
    *keys: str,
) -> str:
    for key in keys:
        value = _text(row.get(key))
        if value:
            return value
        value = _text(raw_json.get(key))
        if value:
            return value
    return ""


def _split_places(value: Any) -> list[str]:
    text = _text(value)
    if not text:
        return []
    return _dedupe(_text(part) for part in _PLACE_SEPARATOR_RE.split(text) if _text(part))


def _normalize_origin(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return _origin_alias_for(text) or text


def _normalize_destination(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if text in _GUANGDONG_ALIASES:
        return "广东侨乡" if text == "广东" else text
    return text


def _infer_origin(place_mentions: list[str]) -> str:
    for place in place_mentions:
        origin = _origin_alias_for(place)
        if origin:
            return origin
    for place in place_mentions:
        if place == "海外":
            return place
    return ""


def _infer_destination(place_mentions: list[str]) -> str:
    for place in place_mentions:
        if _is_guangdong_place(place):
            return place if place.startswith("广东") else "广东侨乡"
    return ""


def _infer_country_or_region(
    *,
    origin: str,
    destination: str,
    place_mentions: list[str],
) -> str:
    values: list[str] = []
    for place in [origin, destination, *place_mentions]:
        country = _country_or_region_for_place(place)
        if country:
            values.append(country)
    return "；".join(_dedupe(values))


def _origin_alias_for(value: str) -> str:
    for normalized, aliases in _ORIGIN_ALIASES:
        if any(alias in value for alias in aliases):
            return normalized
    return ""


def _country_or_region_for_place(value: str) -> str:
    text = _text(value)
    if not text:
        return ""
    origin = _origin_alias_for(text)
    if origin:
        return origin
    if _is_guangdong_place(text):
        return "广东侨乡"
    if text == "海外":
        return "海外"
    return ""


def _is_guangdong_place(value: str) -> bool:
    return any(alias in value for alias in _GUANGDONG_ALIASES)


def _dedupe(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return str(value).strip()
